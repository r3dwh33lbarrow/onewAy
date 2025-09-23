use crate::utils::{str_to_snake_case, title_case_to_camel_case};
use crate::{debug, error, info};
use anyhow::Result;
use serde::Deserialize;
use std::collections::HashMap;
use std::path::Path;
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command as TokioCommand};
use tokio::sync::Mutex;
use tokio::sync::mpsc::UnboundedSender;

#[derive(Debug, Deserialize, PartialEq, Clone)]
#[serde(rename_all = "snake_case")]
pub enum ModuleStart {
    OnStart,
    Manual,
}

#[derive(Debug, Deserialize, Clone)]
pub struct Binaries {
    pub windows: Option<String>,
    pub mac: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct ModuleConfig {
    name: String,
    binaries: Binaries,
    start: ModuleStart,
    pub parent_directory: Option<String>,
}

pub struct ModuleManager {
    modules_directory: String,
    module_configs: Arc<Mutex<Vec<ModuleConfig>>>,
    running: Arc<Mutex<HashMap<String, Arc<Mutex<Child>>>>>,
}

impl ModuleConfig {
    pub fn resolve_binaries(&self) -> Option<&str> {
        #[cfg(target_os = "windows")]
        {
            return self.binaries.windows.as_deref();
        }
        #[cfg(target_os = "macos")]
        {
            return self.binaries.mac.as_deref();
        }
        None
    }
}

impl ModuleManager {
    pub fn new(modules_directory: &str) -> Self {
        Self {
            module_configs: Arc::new(Mutex::new(vec![])),
            modules_directory: modules_directory.to_string(),
            running: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub async fn load_module(
        &mut self,
        config_path: &str,
        parent_dir: Option<String>,
    ) -> Result<()> {
        let config_content = tokio::fs::read_to_string(config_path).await?;
        let mut config: ModuleConfig = serde_yaml::from_str(&config_content)?;
        config.parent_directory = parent_dir;

        let mut configs = self.module_configs.lock().await;
        debug!("Loaded module: {:?}", config);
        configs.push(config);
        Ok(())
    }

    pub async fn load_all_modules(&mut self) -> Result<()> {
        let mut module_folders = Vec::new();
        let mut read_dir = tokio::fs::read_dir(&self.modules_directory).await?;

        while let Some(entry) = read_dir.next_entry().await? {
            let path = entry.path();
            if path.is_dir() {
                if let Some(name) = path.file_name().and_then(|s| s.to_str()) {
                    module_folders.push(name.to_string());
                }
            }
        }

        for folder in module_folders {
            let config_path = Path::new(&self.modules_directory)
                .join(&folder)
                .join("config.yaml");
            let result = match tokio::fs::metadata(&config_path).await {
                Ok(metadata) => metadata.is_file(),
                Err(_) => false,
            };

            if !result {
                error!("Module {} is missing config.yaml", folder);
                continue;
            }

            self.load_module(config_path.to_str().unwrap(), Some(folder))
                .await?
        }

        Ok(())
    }

    pub async fn start_all_modules_by_start(&self, start: ModuleStart) -> Result<()> {
        for config in self.module_configs.lock().await.iter() {
            if config.start == ModuleStart::OnStart {
                info!("Starting module: {}", config.name);

                if let Some(binary) = config.resolve_binaries() {
                    let relative_binary_path = Path::new(&self.modules_directory)
                        .join(str_to_snake_case(&config.name))
                        .join(binary);

                    let mut command = std::process::Command::new(&relative_binary_path);
                    let result = command.spawn();

                    if result.is_err() {
                        let mut command = std::process::Command::new(binary);
                        let result = command.spawn();
                        if result.is_err() {
                            error!(
                                "Failed to start module {} or {}: {}",
                                binary,
                                relative_binary_path.to_str().unwrap().to_string(),
                                result.err().unwrap()
                            );
                        }
                    }
                } else {
                    error!("No compatible binary found for {}", config.name);
                }
            }
        }

        Ok(())
    }

    pub async fn get_module(&self, name: &str) -> Option<ModuleConfig> {
        let configs = self.module_configs.lock().await;
        configs
            .iter()
            .find(|config| {
                config.name == name
                    || title_case_to_camel_case(&config.name) == name
                    || str_to_snake_case(&config.name) == name
            })
            .cloned()
    }

    pub fn get_modules_directory(&self) -> String {
        self.modules_directory.clone()
    }

    pub async fn start_module_streaming(
        &self,
        name: &str,
        sender: UnboundedSender<String>,
    ) -> Result<()> {
        let module_opt = self.get_module(name).await;
        let Some(module) = module_opt else {
            return Ok(());
        };

        let Some(binary) = module.resolve_binaries() else {
            return Ok(());
        };

        let parent_dir = module.parent_directory.clone();
        let mut full_path = std::path::PathBuf::from(self.get_modules_directory());
        if let Some(dir) = parent_dir {
            full_path.push(dir);
        }
        full_path.push(binary);

        let mut cmd = TokioCommand::new(&full_path);
        cmd.stdout(std::process::Stdio::piped());
        cmd.stderr(std::process::Stdio::piped());
        let mut child = cmd.spawn()?;

        let stdout = child.stdout.take();
        let stderr = child.stderr.take();

        let child_arc = Arc::new(Mutex::new(child));
        {
            let mut map = self.running.lock().await;
            map.insert(name.to_string(), Arc::clone(&child_arc));
        }

        let module_name = name.to_string();
        let _ = sender.send(
            serde_json::json!({
                "message_type": "module_started",
                "module_name": module_name
            })
            .to_string(),
        );

        if let Some(stdout) = stdout {
            let sender_clone = sender.clone();
            let module_name = name.to_string();
            tokio::spawn(async move {
                let mut reader = BufReader::new(stdout).lines();
                while let Ok(Some(line)) = reader.next_line().await {
                    let _ = sender_clone.send(
                        serde_json::json!({
                            "message_type": "module_output",
                            "module_name": module_name,
                            "stream": "stdout",
                            "line": line
                        })
                        .to_string(),
                    );
                }
            });
        }

        if let Some(stderr) = stderr {
            let sender_clone = sender.clone();
            let module_name = name.to_string();
            tokio::spawn(async move {
                let mut reader = BufReader::new(stderr).lines();
                while let Ok(Some(line)) = reader.next_line().await {
                    let _ = sender_clone.send(
                        serde_json::json!({
                            "message_type": "module_output",
                            "module_name": module_name,
                            "stream": "stderr",
                            "line": line
                        })
                        .to_string(),
                    );
                }
            });
        }

        let sender_clone = sender.clone();
        let running_map = Arc::clone(&self.running);
        let module_name = name.to_string();
        let child_for_wait = Arc::clone(&child_arc);
        tokio::spawn(async move {
            let code = {
                let mut child = child_for_wait.lock().await;
                let status = child.wait().await.ok();
                status.and_then(|s| s.code()).unwrap_or_default()
            };
            let mut map = running_map.lock().await;
            map.remove(&module_name);

            let _ = sender_clone.send(
                serde_json::json!({
                    "message_type": "module_exit",
                    "module_name": module_name,
                    "code": code
                })
                .to_string(),
            );
        });

        Ok(())
    }

    pub async fn cancel_module(&self, name: &str) -> Result<bool> {
        let map = self.running.lock().await;
        if let Some(child_arc) = map.get(name) {
            let mut child = child_arc.lock().await;
            let _ = child.kill().await;
            return Ok(true);
        }
        Ok(false)
    }
}

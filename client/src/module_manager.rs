use crate::config::CONFIG;
use crate::schemas::BasicTaskResponse;
use crate::schemas::modules::AllInstalledResponse;
use crate::utils::{str_to_snake_case, title_case_to_camel_case};
use crate::{ApiClient, debug, error};
use serde::Deserialize;
use std::collections::{HashMap, HashSet};
use std::io;
use std::path::Path;
use std::sync::Arc;
use thiserror::Error;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin, Command};
use tokio::time::{sleep, Duration};
use tokio::sync::Mutex;
use tokio::sync::mpsc::UnboundedSender;

#[derive(Debug, Error)]
pub enum ModuleManagerError {
    #[error("I/O error: {0}")]
    IO(#[from] io::Error),

    #[error("YAML parsing error: {0}")]
    YAMLParse(#[from] serde_yaml::Error),

    #[error("Module not found: {0}")]
    ModuleNotFound(String),

    #[error("Could not resolve binaries")]
    BinaryResolutionFailed,

    #[error("Not a valid module: {0}")]
    NotAValidModule(String),

    #[error("Module {0} isn't running")]
    ModuleNotRunning(String),

    #[error("Module has no stdin")]
    ModuleHasNoStdin,
}

#[derive(Debug, Deserialize, PartialEq, Clone)]
#[serde(rename_all = "snake_case")]
pub enum ModuleStart {
    OnStart,
    Manual,
}

#[derive(Debug, Deserialize, Clone)]
pub(crate) struct Binaries {
    pub windows: Option<String>,
    pub mac: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub(crate) struct ModuleConfig {
    name: String,
    binaries: Binaries,
    start: ModuleStart,
    pub parent_directory: Option<String>,
}

#[derive(Debug)]
pub(crate) struct RunningChild {
    child: Option<Child>,
    child_stdin: Option<ChildStdin>,
}

pub struct ModuleManager {
    modules_directory: String,
    module_configs: Arc<Mutex<Vec<ModuleConfig>>>,
    running: Arc<Mutex<HashMap<String, Arc<Mutex<RunningChild>>>>>,
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
        #[cfg(not(any(target_os = "windows", target_os = "macos")))]
        {
            return None;
        }
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

    async fn load_module(
        &mut self,
        config_path: &str,
        parent_dir: Option<String>,
    ) -> Result<(), ModuleManagerError> {
        let config_content = tokio::fs::read_to_string(config_path).await?;
        let mut config: ModuleConfig = serde_yaml::from_str(&config_content)?;
        config.parent_directory = parent_dir;

        let mut configs = self.module_configs.lock().await;
        let config_clone = config.clone();
        configs.push(config);
        debug!("Loaded module: {:?}", config_clone);
        Ok(())
    }

    pub async fn load_all_modules(&mut self) -> Result<(), ModuleManagerError> {
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

    async fn start_module(&self, module: ModuleConfig) -> Result<(), ModuleManagerError> {
        if let Some(binary) = module.resolve_binaries() {
            let relative_path = Path::new(&self.modules_directory)
                .join(str_to_snake_case(&module.name))
                .join(binary);

            let child = if relative_path.is_file() {
                Command::new(&relative_path)
                    .spawn()
                    .map_err(ModuleManagerError::IO)?
            } else if Path::new(binary).is_file() {
                Command::new(binary)
                    .spawn()
                    .map_err(ModuleManagerError::IO)?
            } else {
                return Err(ModuleManagerError::ModuleNotFound(format!(
                    "Binary not found at {} or {}",
                    relative_path.display(),
                    binary
                )));
            };

            let mut running = self.running.lock().await;
            running.insert(
                module.name.clone(),
                Arc::new(Mutex::new(RunningChild {
                    child: Some(child),
                    child_stdin: None,
                })),
            );

            debug!("Started module: {}", module.name);
            Ok(())
        } else {
            Err(ModuleManagerError::BinaryResolutionFailed)
        }
    }

    pub(crate) async fn start_module_streaming(
        &self,
        name: &str,
        sender: UnboundedSender<String>,
    ) -> Result<(), ModuleManagerError> {
        let module_opt = self.get_module(name).await;
        let Some(module) = module_opt else {
            return Err(ModuleManagerError::ModuleNotFound(name.to_string()));
        };
        let Some(binary) = module.resolve_binaries() else {
            return Err(ModuleManagerError::BinaryResolutionFailed);
        };

        let parent_dir = module.parent_directory.clone();
        let mut full_path = std::path::PathBuf::from(self.get_modules_directory());
        if let Some(dir) = parent_dir {
            full_path.push(dir);
        }
        full_path.push(binary);

        let mut cmd = Command::new(&full_path);
        cmd.stdout(std::process::Stdio::piped());
        cmd.stderr(std::process::Stdio::piped());
        cmd.stdin(std::process::Stdio::piped());
        let mut child = cmd.spawn()?;

        let stdout = child.stdout.take();
        let stderr = child.stderr.take();
        let stdin = child.stdin.take().ok_or_else(|| {
            ModuleManagerError::IO(io::Error::new(
                io::ErrorKind::Other,
                "Failed to capture stdin",
            ))
        })?;

        let child_arc = Arc::new(Mutex::new(RunningChild {
            child: Some(child),
            child_stdin: Some(stdin),
        }));
        {
            let mut map = self.running.lock().await;
            map.insert(name.to_string(), Arc::clone(&child_arc));
        }

        let module_name = name.to_string();
        let _ = sender.send(
            serde_json::json!({
                "type": "module_started",
                "event": {
                    "module_name": module_name
                }
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
                            "type": "console_output",
                            "output": {
                                "module_name": module_name,
                                "stream": "stdout",
                                "line": line
                            }
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
                            "type": "console_output",
                            "output": {
                                "module_name": module_name,
                                "stream": "stderr",
                                "line": line
                            }
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
            // Poll the child exit without holding the lock to allow stdin writes and cancel.
            let code = loop {
                let done = {
                    let mut guard = child_for_wait.lock().await;
                    if let Some(ch) = guard.child.as_mut() {
                        match ch.try_wait() {
                            Ok(Some(status)) => break status.code().unwrap_or_default(),
                            Ok(None) => false,
                            Err(_) => break 0,
                        }
                    } else {
                        // No child present -> treat as exited
                        break 0;
                    }
                };
                if !done {
                    sleep(Duration::from_millis(100)).await;
                }
            };
            let mut map = running_map.lock().await;
            map.remove(&module_name);

            let _ = sender_clone.send(
                serde_json::json!({
                    "type": "module_exit",
                    "event": {
                        "module_name": module_name,
                        "code": code
                    }
                })
                .to_string(),
            );
        });

        Ok(())
    }

    pub async fn give_to_stdin(
        &self,
        module_name: &str,
        bytes: &[u8],
    ) -> Result<(), ModuleManagerError> {
        
        let module = self.get_module(module_name).await;
        if module.is_none() {
            return Err(ModuleManagerError::ModuleNotFound(module_name.to_string()));
        }

        let running = self.running.lock().await;
        let running_module = running.get(module_name);
        if running_module.is_none() {
            return Err(ModuleManagerError::ModuleNotRunning(
                module_name.to_string(),
            ));
        }

        let running_child = running_module.unwrap();
        let mut child_lock = running_child.lock().await;

        if let Some(ref mut stdin) = child_lock.child_stdin {
            stdin
                .write_all(bytes)
                .await
                .map_err(ModuleManagerError::IO)?;
            stdin.flush().await.map_err(ModuleManagerError::IO)?;
            Ok(())
        } else {
            Err(ModuleManagerError::ModuleHasNoStdin)
        }
    }

    pub async fn start_all_modules_by_start(
        &self,
        start_type: ModuleStart,
    ) -> Result<(), ModuleManagerError> {
        let configs = self.module_configs.lock().await;
        let matching_modules: Vec<ModuleConfig> = configs
            .iter()
            .filter(|config| config.start == start_type)
            .cloned()
            .collect();
        drop(configs);

        for module in matching_modules {
            if let Err(e) = self.start_module(module.clone()).await {
                error!("Failed to start module {}: {}", module.name, e);
                return Err(e);
            }
        }

        Ok(())
    }

    pub(crate) async fn get_module(&self, name: &str) -> Option<ModuleConfig> {
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

    fn get_modules_directory(&self) -> String {
        self.modules_directory.to_string()
    }

    pub(crate) async fn cancel_module(&self, name: &str) -> bool {
        let map = self.running.lock().await;
        if let Some(child_arc) = map.get(name) {
            let mut child = child_arc.lock().await;
            if let Some(ch) = &mut child.child {
                let _ = ch.kill().await;
            }
            return true;
        }

        false
    }

    pub async fn check_installed_discrepancies(
        &self,
        api_client: Arc<Mutex<ApiClient>>,
    ) -> anyhow::Result<Vec<String>> {
        let local_modules = self.module_configs.lock().await;
        let local_module_names: Vec<String> =
            local_modules.iter().map(|x| x.name.to_string()).collect();

        let api_client = api_client.lock().await;
        let remote_modules = api_client
            .get::<AllInstalledResponse>(&format!("/module/installed/{}", CONFIG.auth.username))
            .await?;
        let remote_module_names: HashSet<String> = remote_modules
            .all_installed
            .unwrap_or_default()
            .iter()
            .map(|x| x.name.to_string())
            .collect();

        let discrepancies: Vec<String> = local_module_names
            .into_iter()
            .filter(|name| !remote_module_names.contains(name))
            .collect();

        Ok(discrepancies)
    }

    pub async fn set_installed(
        &self,
        module_name: &str,
        api_client: Arc<Mutex<ApiClient>>,
    ) -> anyhow::Result<BasicTaskResponse> {
        let api_client = api_client.lock().await;
        let camel_case_name = title_case_to_camel_case(module_name);
        api_client
            .post_with_query::<(), BasicTaskResponse>(
                &format!("/module/set-installed/{}", CONFIG.auth.username),
                &[("module_name", &camel_case_name)],
                &(),
            )
            .await
    }
}

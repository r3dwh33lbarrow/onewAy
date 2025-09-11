use anyhow::Result;
use serde::Deserialize;
use std::path::Path;
use std::sync::Arc;
use tokio::sync::Mutex;
use crate::utils::str_to_snake_case;
use crate::{debug, error, info};

#[derive(Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ModuleStart {
    OnStart,
}

#[derive(Deserialize)]
pub struct Binaries {
    pub windows: Option<String>,
    pub mac: Option<String>,
}

#[derive(Deserialize)]
pub struct ModuleConfig {
    name: String,
    binaries: Binaries,
    start: ModuleStart,
}

pub struct ModuleManager {
    modules_directory: String,
    module_configs: Arc<Mutex<Vec<ModuleConfig>>>,
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
        }
    }

    pub async fn load_module(&mut self, config_path: &str) -> Result<()> {
        let config_content = tokio::fs::read_to_string(config_path).await?;
        let config: ModuleConfig = serde_yaml::from_str(&config_content)?;
        let name = config.name.clone();

        let mut configs = self.module_configs.lock().await;
        configs.push(config);
        debug!("Loaded module: {}", name);
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

            self.load_module(config_path.to_str().unwrap()).await?
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
}

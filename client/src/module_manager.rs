use crate::{debug, error};
use serde::Deserialize;
use std::collections::HashMap;
use std::io;
use std::path::Path;
use std::sync::Arc;
use thiserror::Error;
use tokio::process::Child;
use tokio::sync::Mutex;
use crate::utils::{str_to_snake_case, title_case_to_camel_case};

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
}

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

    pub async fn start_module(&self, module: ModuleConfig) -> Result<(), ModuleManagerError> {
        if let Some(binary) = module.resolve_binaries() {
            let relative_path = Path::new(&self.modules_directory)
                .join(str_to_snake_case(&module.name))
                .join(binary);

            let child = if relative_path.is_file() {
                tokio::process::Command::new(&relative_path)
                    .spawn()
                    .map_err(ModuleManagerError::IO)?
            } else if Path::new(binary).is_file() {
                tokio::process::Command::new(binary)
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
            running.insert(module.name.clone(), Arc::new(Mutex::new(child)));

            debug!("Started module: {}", module.name);
            Ok(())
        } else {
            Err(ModuleManagerError::BinaryResolutionFailed)
        }
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
        self.modules_directory.to_string()
    }
}
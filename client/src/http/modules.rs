use crate::http::api_client::ApiClient;
use crate::schemas::modules::ModuleAllResponse;
use crate::{debug, error};
use crate::utils::snake_case_to_camel_case;
use anyhow::Result;
use serde::Deserialize;
use serde_yaml;
use std::path::Path;
use tokio::fs;
use tokio::fs::ReadDir;

#[derive(Deserialize)]
struct ModuleConfig {
    name: String,
    binary: String,
    start: String,
}

enum ModuleStart {
    OnStart,
}

pub struct Module {
    name: String,
    binary: String,
    start: String,
}

pub async fn get_all_modules(api_client: &ApiClient) -> Result<ModuleAllResponse> {
    match api_client.get::<ModuleAllResponse>("/user/modules/all").await {
        Ok(response) => Ok(response),
        Err(error) => {
            error!("Error getting modules: {:?}", error);
            Err(error)
        }
    }
}

pub async fn load_module(config_path: &str) -> Result<Module> {
    let config_content = tokio::fs::read_to_string(config_path).await?;
    let config: ModuleConfig = serde_yaml::from_str(&config_content)?;

    let start_camel = snake_case_to_camel_case(&config.start);

    Ok(Module {
        name: config.name,
        binary: config.binary,
        start: start_camel,
    })
}

pub async fn load_modules(modules_directory: &str) -> Result<Vec<Module>> {
    debug!("Loading modules from {}", modules_directory);
    let mut module_folders = Vec::new();
    let mut loaded_modules = Vec::new();

    let mut read_dir: ReadDir = fs::read_dir(&modules_directory).await?;
    while let Some(entry) = read_dir.next_entry().await? {
        let path = entry.path();
        if path.is_dir() {
            if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                module_folders.push(name.to_string());
            }
        }
    }

    for module_folder in module_folders {
        debug!("Loading module from directory {}", module_folder);

        let config_path = Path::new(&modules_directory).join(&module_folder).join("config.yaml");
        let result = match fs::metadata(&config_path).await {
            Ok(metadata) => metadata.is_file(),
            Err(_) => false,
        };

        if !result {
            error!("Module {} is missing config.yaml", module_folder);
            continue;
        }

        // Load the module using the load_module function
        match load_module(config_path.to_str().unwrap()).await {
            Ok(module) => {
                debug!("Successfully loaded module: {}", module.name);
                loaded_modules.push(module);
            }
            Err(err) => {
                error!("Failed to load module from {}: {:?}", module_folder, err);
            }
        }
    }

    Ok(loaded_modules)
}
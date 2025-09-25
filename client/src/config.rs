use crate::utils;
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use std::fs;
use std::io;
use std::sync::Arc;
use toml;

pub static CONFIG_PATH: Lazy<String> =
    Lazy::new(|| utils::resolve_current_dir("[CURRENT_DIR]/config.toml"));

#[derive(Serialize, Deserialize, Debug)]
pub struct ModuleConfig {
    pub version: String,
    pub modules_directory: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct AuthConfig {
    pub username: String,
    pub password: String,
    pub enrolled: bool,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Config {
    pub module: ModuleConfig,
    pub auth: AuthConfig,
}

pub static CONFIG: Lazy<Arc<Config>> = Lazy::new(|| {
    let toml_str = fs::read_to_string(CONFIG_PATH.as_str()).expect("Failed to read config.toml");
    let config: Config = toml::from_str(&toml_str).expect("Failed to parse config.toml");
    Arc::new(config)
});

pub fn set_enrolled() -> Result<(), io::Error> {
    let content = fs::read_to_string(CONFIG_PATH.as_str())?;
    let mut config: Config =
        toml::from_str(&content).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

    config.auth.enrolled = true;

    let new_content =
        toml::to_string(&config).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

    fs::write(CONFIG_PATH.as_str(), new_content)?;
    Ok(())
}

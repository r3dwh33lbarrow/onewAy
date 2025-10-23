use crate::utils;
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use std::fs;
use std::sync::Arc;
use toml;

static CONFIG_PATH: Lazy<String> =
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
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Config {
    pub debug: Option<bool>,
    pub output_override: Option<bool>,  // Output override will enable logging in release mode
    pub module: ModuleConfig,
    pub auth: AuthConfig,
}

pub static CONFIG: Lazy<Arc<Config>> = Lazy::new(|| {
    let toml_str = fs::read_to_string(CONFIG_PATH.as_str()).expect("Failed to read config.toml");
    let mut config: Config = toml::from_str(&toml_str).expect("Failed to parse config.toml");
    config.module.modules_directory = utils::resolve_current_dir(&config.module.modules_directory);

    Arc::new(config)
});

use std::fs;
use std::sync::Arc;
use once_cell::sync::Lazy;
use serde::{Serialize, Deserialize};
use toml;

#[derive(Serialize, Deserialize)]
pub struct ModuleConfig {
    pub version: String,
    pub modules_directory: String,
}

#[derive(Serialize, Deserialize)]
pub struct AuthConfig {
    pub username: String,
    pub password: String,
    pub enrolled: bool,
}

#[derive(Serialize, Deserialize)]
pub struct Config {
    pub module: ModuleConfig,
    pub auth: AuthConfig,
}

pub static CONFIG: Lazy<Arc<Config>> = Lazy::new(|| {
    let toml_str = fs::read_to_string("config.toml").expect("Failed to read config.toml");
    let config: Config = toml::from_str(&toml_str).expect("Failed to parse config.toml");
    Arc::new(config)
});

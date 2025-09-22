use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use std::env;
use std::fs;
use std::sync::Arc;
use toml;

pub static CONFIG_PATH: Lazy<String> = Lazy::new(|| {
    resolve_current_dir("[CURRENT_DIR]/config.toml")
});

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

pub fn resolve_current_dir(path: &str) -> String {
    path.replace(
        "[CURRENT_DIR]",
        env::current_dir()
            .expect("Failed to get current dir")
            .to_str()
            .unwrap(),
    )
}

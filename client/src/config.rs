use std::fs;
use std::sync::Arc;
use once_cell::sync::Lazy;
use serde::{Serialize, Deserialize};
use toml;

#[derive(Serialize, Deserialize)]
struct ModuleConfig {
    version: String,
}

#[derive(Serialize, Deserialize)]
struct AuthConfig {
    username: String,
    password: String,
    enrolled: bool,
}

#[derive(Serialize, Deserialize)]
struct Config {
    module: ModuleConfig,
    auth: AuthConfig,
}

pub static CONFIG: Lazy<Arc<Config>> = Lazy::new(|| {
    let toml_str = fs::read_to_string("config.toml").expect("Failed to read config.toml");
    let config: Config = toml::from_str(&toml_str).expect("Failed to parse config.toml");
    Arc::new(config)
});

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_read_config() {
        assert_eq!(CONFIG.auth.username, "test_0")
    }
}
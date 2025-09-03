use crate::error;
use serde::Deserialize;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::Path;

#[derive(Default, Deserialize)]
pub struct ConfigData {
    file_name: String,
    pub username: String,
    pub password: String,
    pub enrolled: bool,
    pub version: String,
    pub modules_directory: String,
}

impl ConfigData {
    pub fn load(file_name: &Path) -> anyhow::Result<Self> {
        let mut config = ConfigData::default();
        let file = File::open(file_name)?;
        let reader = BufReader::new(file);
        config.file_name = file_name.to_str().unwrap().to_string();

        for line in reader.lines() {
            let line = line?;

            if let Some((key_original, value_original)) = line.split_once("=") {
                let key = key_original.to_lowercase();
                let value = value_original.trim_end();

                if key == "username" {
                    config.username = value.to_string();
                } else if key == "password" {
                    config.password = value.to_string();
                } else if key == "enrolled" {
                    match value.parse::<bool>() {
                        Ok(b) => config.enrolled = b,
                        Err(_) => {
                            error!(
                                "Failed to parse 'enrolled' in {}: expected 'true' or 'false', got {}",
                                file_name.display(),
                                value
                            );
                        }
                    }
                } else if key == "version" {
                    config.version = value.to_string();
                } else if key == "modules_directory" {
                    config.modules_directory = parse_root(value);
                } else {
                    error!(
                        "Invalid key found in {}: {}",
                        file_name.display(),
                        key_original
                    );
                }
            }
        }

        Ok(config)
    }

    pub fn replace<T: std::fmt::Display>(
        &mut self,
        key: &str,
        new_value: &T,
    ) -> anyhow::Result<()> {
        let file = File::open(&self.file_name)?;
        let reader = BufReader::new(file);
        let mut lines = Vec::new();
        let mut found = false;

        for line_result in reader.lines() {
            let line = line_result?;

            if let Some((key_original, _)) = line.split_once('=') {
                let key_lower = key_original.trim().to_lowercase();
                if key_lower == key.to_lowercase() {
                    // This is the line we want to replace
                    lines.push(format!("{}={}", key_original, new_value));
                    found = true;
                } else {
                    lines.push(line);
                }
            } else {
                lines.push(line);
            }
        }

        if !found {
            lines.push(format!("{}={}", key, new_value));
        }

        let mut file = OpenOptions::new()
            .write(true)
            .truncate(true)
            .open(&self.file_name)?;

        for line in lines {
            writeln!(file, "{}", line)?;
        }

        match key.to_lowercase().as_str() {
            "username" => self.username = new_value.to_string(),
            "password" => self.password = new_value.to_string(),
            "enrolled" => {
                if let Ok(b) = new_value.to_string().parse::<bool>() {
                    self.enrolled = b;
                } else {
                    error!(
                        "Failed to parse 'enrolled' in {}: expected 'true' or 'false', got {}",
                        self.file_name, new_value
                    );
                }
            }
            "version" => self.version = new_value.to_string(),
            _ => {
                error!("Invalid key found in {}: {}", self.file_name, key);
            }
        }

        Ok(())
    }
}

fn parse_root(path: &str) -> String {
    if path.contains("[ROOT]") {
        let env_path = std::env::current_dir()
            .unwrap_or_else(|_| std::path::PathBuf::from("."))
            .join(".env");

        let root_dir = env_path
            .parent()
            .and_then(|p| p.parent())
            .unwrap_or_else(|| Path::new("."));

        let path_with_root = path.replace("[ROOT]", root_dir.to_str().unwrap_or("."));

        let normalized_path = if cfg!(windows) {
            path_with_root.replace('/', "\\")
        } else {
            path_with_root
        };

        std::path::PathBuf::from(normalized_path)
            .to_str()
            .unwrap_or(path)
            .to_string()
    } else {
        path.to_string()
    }
}

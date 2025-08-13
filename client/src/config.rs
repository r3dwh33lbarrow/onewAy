use std::fs::File;
use std::io::{BufRead, BufReader, Result};
use std::path::Path;

#[derive(Default)]
pub struct ConfigData {
    username: String,
    password: String,
    enrolled: bool,
}

impl ConfigData {
    pub fn get(file_path: &Path) -> Result<Self> {
        let file = File::open(file_path)?;
        let reader = BufReader::new(file);

        let mut cfg = Self::default();

        for line in reader.lines() {
            let line = line?;

            if let Some((key, value)) = line.split_once('=') {
                match key.trim() {
                    "username" => cfg.username = value.trim().to_string(),
                    "password" => cfg.password = value.trim().to_string(),
                    "enrolled" => {
                        if value.trim().to_string() == "true" {
                            cfg.enrolled = true;
                        } else {
                            cfg.enrolled = false;
                        }
                    }
                    _ => {}
                }
            }
        }

        Ok(cfg)
    }

    pub fn username(&self) -> &str {
        &self.username
    }

    pub fn password(&self) -> &str {
        &self.password
    }

    pub fn enrolled(&self) -> bool {
        self.enrolled
    }
}
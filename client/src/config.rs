use serde::Deserialize;

#[derive(Deserialize)]
pub struct ConfigData {
    pub username: String,
    pub password: String,
    pub enrolled: bool,
    pub version: String
}
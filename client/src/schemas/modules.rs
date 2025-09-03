use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct ModuleBasicInfo {
    name: String,
    version: String,
    binaries_platform: Vec<String>,
}

#[derive(Serialize, Deserialize)]
pub struct ModuleAllResponse {
    modules: Vec<ModuleBasicInfo>,
}
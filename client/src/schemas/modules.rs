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

#[derive(Debug, Serialize, Deserialize)]
pub struct InstalledModuleInfo {
    pub name: String,
    pub description: Option<String>,
    pub version: String,
    pub status: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AllInstalledResponse {
    pub all_installed: Vec<InstalledModuleInfo>,
}
use serde::{Deserialize, Serialize};

// Public so other modules can deserialize and read fields from /module/all
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct ModuleBasicInfo {
    pub name: String,
    pub version: String,
    pub binaries_platform: Vec<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct ModuleAllResponse {
    pub modules: Vec<ModuleBasicInfo>,
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
    pub all_installed: Option<Vec<InstalledModuleInfo>>,
}

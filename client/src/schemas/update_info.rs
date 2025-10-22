use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize)]
pub struct ClientUpdateInfo {
    pub ip_address: Option<String>,
    pub hostname: Option<String>,
    pub client_version: Option<String>,
}
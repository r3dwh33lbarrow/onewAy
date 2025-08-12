use serde::{Serialize, Deserialize};

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct ClientEnrollRequest {
    pub username: String,
    pub password: String,
    pub client_version: String,
}
use serde::{Deserialize, Serialize};

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct ClientEnrollRequest {
    pub username: String,
    pub password: String,
    pub client_version: String,
}

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct ClientLoginRequest {
    pub username: String,
    pub password: String,
}

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct TokenResponse {
    pub refresh_token: String,
    pub token_type: String,
}

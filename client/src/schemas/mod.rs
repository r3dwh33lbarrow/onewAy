pub mod auth;
pub(crate) mod module_bucket;
pub mod modules;
pub mod update_info;
pub mod websockets;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct RootResponse {
    pub message: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct BasicTaskResponse {
    pub result: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ApiErrorResponse {
    pub detail: String,
}

#[derive(Debug)]
pub struct ApiError {
    pub status_code: i32,
    pub detail: String,
}

impl std::fmt::Display for ApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "API Error ({}): {}", self.status_code, self.detail)
    }
}

impl std::error::Error for ApiError {}

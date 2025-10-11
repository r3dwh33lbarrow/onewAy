use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct WebsocketMessage {
    pub(crate) message_type: String,
    pub(crate) module_name: String,
    pub(crate) payload: Option<Vec<u8>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AccessTokenResponse {
    pub(crate) access_token: String,
    token_type: String,
}

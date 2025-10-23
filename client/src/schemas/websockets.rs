use serde::{Deserialize, Serialize};

// Incoming WebSocket messages to the client (from server)
#[derive(Debug, Deserialize, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Message {
    Ping,
    ModuleRun {
        from: String,
        module: ModuleForRun,
    },
    ModuleStdin {
        from: String,
        stdin: ModuleStdinPayload,
    },
    ModuleCancel {
        from: String,
        event: ModuleCancelPayload,
    },
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ModuleForRun {
    pub name: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ModuleStdinPayload {
    pub module_name: String,
    pub data: Vec<u8>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ModuleCancelPayload {
    pub module_name: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct AccessTokenResponse {
    pub(crate) access_token: String,
    token_type: String,
}

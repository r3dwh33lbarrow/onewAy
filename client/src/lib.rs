pub mod config;
pub mod http;
pub mod logger;
pub mod module_manager;
pub mod schemas;
pub mod update;
pub mod utils;

// Re-export primary API so binaries can `use client::*` cleanly.
pub use config::{set_enrolled, CONFIG};
pub use http::api_client::ApiClient;
pub use http::auth::{enroll, login};
pub use http::websockets::start_websocket_client;
pub use module_manager::{ModuleManager, ModuleStart};

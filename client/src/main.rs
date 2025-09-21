mod config;
mod http;
mod logger;
mod module_manager;
mod schemas;
mod system_info;
mod update;
mod utils;

use crate::config::CONFIG;
use crate::http::api_client::ApiClient;
use crate::http::auth::{enroll, login};
use crate::http::websockets::start_websocket_client;
use crate::module_manager::{ModuleManager, ModuleStart};
use std::path::Path;
use std::sync::Arc;

#[tokio::main]
async fn main() {
    let config = CONFIG.clone();
    let mut api_client =
        ApiClient::new("http://127.0.0.1:8000/").expect("failed to initialize ApiClient");

    if ! {
        let result = enroll(
            &api_client,
            &*config_data.username,
            &*config_data.password,
            &*config_data.version,
        )
        .await;
        if !result {
            panic!("failed to enroll client");
        }

        config_data
            .replace("enrolled", &true)
            .expect("failed to save config data");
    } else {
        debug!("Client already enrolled");
    }

    if !login(
        &mut api_client,
        &*config_data.username,
        &*config_data.password,
    )
    .await
    {
        panic!("failed to login");
    }

    debug!("Client logged in");
    debug!("Loading modules from {}", config_data.modules_directory);
    let mut module_manager = ModuleManager::new(&config_data.modules_directory);
    if let Err(e) = module_manager.load_all_modules().await {
        error!("Failed to load modules: {}", e);
    }

    if let Err(e) = module_manager
        .start_all_modules_by_start(ModuleStart::OnStart)
        .await
    {
        error!("Failed to start modules: {}", e);
    }

    let module_manager = Arc::new(module_manager);

    debug!("Starting Websocket client...");
    let api_client_clone = api_client.clone();
    let module_manager_clone = Arc::clone(&module_manager);
    let handle = tokio::spawn(async move {
        start_websocket_client(
            "ws://127.0.0.1:8000/ws-client",
            &api_client_clone,
            module_manager_clone,
        )
        .await
    });

    handle
        .await
        .unwrap()
        .expect("failed to start websocket client");
}

mod config;
mod http;
mod logger;
mod schemas;
mod utils;
mod module_manager;

use std::path::Path;
use crate::config::ConfigData;
use crate::http::api_client::ApiClient;
use crate::http::auth::{enroll, login};
use crate::module_manager::{ModuleManager, ModuleStart};

#[tokio::main]
async fn main() {
    let mut config_data: ConfigData = ConfigData::load(Path::new(".env")).unwrap();

    let mut api_client =
        ApiClient::new("http://127.0.0.1:8000/").expect("failed to initialize ApiClient");

    if !config_data.enrolled {
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

        config_data.replace("enrolled", &true).expect("failed to save config data");
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

    debug!("Loading modules from {}", config_data.modules_directory);
    let mut module_manager = ModuleManager::new(&config_data.modules_directory);
    if let Err(e) = module_manager.load_all_modules().await {
        eprintln!("Failed to load modules: {}", e);
    }

    if let Err(e) = module_manager.start_all_modules_by_start(ModuleStart::OnStart).await {
        eprintln!("Failed to start modules: {}", e);
    }
}

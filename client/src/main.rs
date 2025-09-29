use client::{
    ApiClient, CONFIG, ModuleManager, ModuleStart, debug, enroll, error, login, set_enrolled,
    start_websocket_client,
};
use std::sync::Arc;

#[tokio::main]
async fn main() {
    let config = CONFIG.clone();
    let mut api_client =
        ApiClient::new("http://127.0.0.1:8000/").expect("failed to initialize ApiClient");

    if !config.auth.enrolled {
        let result = enroll(
            &api_client,
            config.auth.username.as_str(),
            config.auth.password.as_str(),
            config.module.version.as_str(),
        )
        .await;
        if !result {
            panic!("failed to enroll client");
        }

        set_enrolled().expect("failed to save enrolled status");
    } else {
        debug!("Client already enrolled");
    }

    if !login(
        &mut api_client,
        config.auth.username.as_str(),
        config.auth.password.as_str(),
    )
    .await
    {
        panic!("failed to login");
    }

    debug!("Client logged in");
    debug!("Loading modules from {}", config.module.modules_directory);
    let mut module_manager = ModuleManager::new(&config.module.modules_directory);
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

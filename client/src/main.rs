use client::{
    ApiClient, CONFIG, ModuleManager, ModuleStart, debug, error, info, login,
    start_websocket_client, warn,
};
use std::sync::Arc;
use tokio::sync::Mutex;

#[tokio::main]
async fn main() {
    let ip: &str = option_env!("IP").unwrap_or("127.0.0.1");
    let port: &str = option_env!("PORT").unwrap_or("8000");

    let base_url = format!("http://{}:{}/", ip, port);
    let websocket_url = format!("ws://{}:{}/ws-client", ip, port);
    let config = CONFIG.clone();
    let api_client = Arc::new(Mutex::new(
        ApiClient::new(&base_url).expect("failed to initialize ApiClient"),
    ));

    println!("{:?}", config);

    if !login(
        Arc::clone(&api_client),
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
    if let Err(e) = module_manager.load_all_modules(api_client.clone()).await {
        error!("Failed to load modules: {}", e);
    }

    let installed_discrepancies = module_manager
        .check_installed_discrepancies(Arc::clone(&api_client))
        .await;
    match installed_discrepancies {
        Ok(installed) => {
            if !installed.is_empty() {
                warn!(
                    "Installed module discrepancies with server: {:?}",
                    installed
                );
                for discrepancy in installed {
                    let result = module_manager
                        .set_installed(&*discrepancy, Arc::clone(&api_client))
                        .await;
                    match result {
                        Ok(..) => info!("Resolved discrepancy: {}", discrepancy),
                        Err(e) => error!("Failed to resolve discrepancy ({}): {}", discrepancy, e),
                    }
                }
            }
        }
        Err(e) => {
            error!("Failed to get module discrepancies: {}", e)
        }
    }

    if let Err(e) = module_manager
        .start_all_modules_by_start(ModuleStart::OnStart, api_client.clone())
        .await
    {
        error!("Failed to start modules: {}", e);
    }

    let module_manager = Arc::new(module_manager);

    debug!("Starting Websocket client...");
    let api_client_clone = api_client.clone();
    let module_manager_clone = Arc::clone(&module_manager);
    let handle = tokio::spawn(async move {
        start_websocket_client(&websocket_url, api_client_clone, module_manager_clone).await
    });

    handle
        .await
        .unwrap()
        .expect("failed to start websocket client");
}

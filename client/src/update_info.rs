use crate::schemas::BasicTaskResponse;
use crate::schemas::update_info::ClientUpdateInfo;
use crate::{ApiClient, error};
use hostname::get;
use std::sync::Arc;
use tokio::sync::Mutex;

fn get_hostname() -> Option<String> {
    match get() {
        Ok(name) => Some(name.into_string().unwrap()),
        Err(_) => None,
    }
}

pub async fn update_info(api_client: Arc<Mutex<ApiClient>>) {
    let api_client = api_client.lock().await;
    let hostname = get_hostname();
    let platform = match std::env::consts::OS {
        "macos" => Some("mac".to_string()),
        "windows" => Some("windows".to_string()),
        "linux" => Some("linux".to_string()),
        _ => None,
    };

    let client_info = ClientUpdateInfo {
        ip_address: None,
        hostname,
        client_version: None,
        platform,
    };
    let result = api_client
        .post::<ClientUpdateInfo, BasicTaskResponse>("/client/update-info", &client_info)
        .await;
    if let Err(e) = result {
        error!("Failed to update client info: {}", e);
    }
}

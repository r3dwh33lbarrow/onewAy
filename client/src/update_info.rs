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
    let hostname = get_hostname().unwrap_or_else(|| "N/A".to_string());
    let client_info = ClientUpdateInfo {
        ip_address: None,
        hostname: Some(hostname),
        client_version: None,
    };
    let result = api_client
        .post::<ClientUpdateInfo, BasicTaskResponse>("/client/update-info", &client_info)
        .await;
    if let Err(e) = result {
        error!("Failed to update client info: {}", e);
    }
}

mod config;
mod http;
mod logger;
mod schemas;

use crate::config::ConfigData;
use crate::http::api_client::ApiClient;
use crate::http::auth::{enroll, login};
use std::path::Path;

#[tokio::main]
async fn main() {
    let config_data = ConfigData::get(Path::new("SECRET")).expect("failed to get config file");
    let api_client =
        ApiClient::new("http://127.0.0.1:8000/").expect("failed to initialize ApiClient");

    if !config_data.enrolled() {
        let result = enroll(
            &api_client,
            config_data.username(),
            config_data.password(),
            config_data.version(),
        )
        .await;
        if !result {
            panic!("Failed to enroll client");
        }
    } else {
        debug!("Client already enrolled");
    }

    if !login(&api_client, config_data.username(), config_data.password()).await {
        panic!("Failed to login");
    }
}

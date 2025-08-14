mod config;
mod http;
mod logger;
mod schemas;

use crate::config::ConfigData;
use crate::http::api_client::ApiClient;
use crate::http::auth::{enroll, login};
use std::path::Path;
use dotenv::dotenv;
use crate::schemas::BasicTaskResponse;

#[tokio::main]
async fn main() {
    dotenv().ok();
    let config_data: ConfigData =
        envy::from_env().unwrap_or_else(|e| panic!("failed to load config: {e}"));

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
    } else {
        debug!("Client already enrolled");
    }

    if !login(&mut api_client, &*config_data.username, &*config_data.password).await {
        panic!("failed to login");
    }

    let url = format!("/client/auth/{}/check", config_data.username);
    api_client.get::<BasicTaskResponse>(&url)
        .await
        .expect("login check failed");
}

mod config;
mod http;
mod logger;
mod schemas;

use std::path::Path;
use serde::{Deserialize, Serialize};
use crate::config::ConfigData;
use crate::http::api_client::ApiClient;
use crate::http::auth::{enroll, login, refresh_access_token};
use crate::schemas::BasicTaskResponse;
use crate::schemas::ApiError;

#[derive(Serialize, Deserialize)]
struct AddRequest {
    module_path: String,
}
#[derive(Serialize, Deserialize)]
struct AddResponse {
    result: String,
}

#[tokio::main]
async fn main() {
    let config_data: ConfigData = ConfigData::load(Path::new(".env")).unwrap();
    let mut api_client =
        ApiClient::new("http://localhost:8000/").expect("failed to initialize ApiClient");

    if !login(&mut api_client, &*config_data.username, &*config_data.password).await {
        panic!("failed to login");
    }

    let add_response = AddRequest {
        module_path: "C:/Users/morgant/Projects/onewAy/modules/test_module".to_string(),
    };
    let result = api_client.post::<AddRequest, AddResponse>("/user/modules/add", &add_response).await;
    match result {
        Ok(response) if response.result == "success" => {
            println!("Module added successfully");
        }
        Ok(_) => {
            println!("Module add failed");
        }
        Err(e) => {
            // Check if this is an API error with detailed information
            if let Some(api_error) = e.downcast_ref::<ApiError>() {
                println!("API Error {}: {}", api_error.status_code, api_error.detail);
            } else {
                // Fallback for non-API errors (network issues, etc.)
                println!("Failed to add module: {}", e);
            }
        }
    }
}


async fn _main() {
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

    let url = format!("/client/auth/{}/check", config_data.username);
    api_client
        .get::<BasicTaskResponse>(&url)
        .await
        .expect("login check failed");

    if !refresh_access_token(&mut api_client).await {
        panic!("failed to refresh token");
    }

    api_client
        .get::<BasicTaskResponse>(&url)
        .await
        .expect("login check 2 failed");
}

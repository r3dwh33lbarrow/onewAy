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
        module_path: "C:/Users/morgant/Projects/onewAy/client/modules/".to_string(),
    };
    let result = api_client.post::<AddRequest, AddResponse>("/user/modules/add", &add_response).await;
    if result.unwrap().result == "success" {
        println!("Module added successfully");
    } else {
        println!("Module add failed");
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

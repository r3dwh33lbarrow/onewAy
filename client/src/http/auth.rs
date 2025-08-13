use crate::http::api_client::ApiClient;
use crate::schemas::BasicTaskResponse;
use crate::schemas::auth::{ClientEnrollRequest, ClientLoginRequest, TokenResponse};
use crate::{error, info};

pub async fn enroll(
    api_client: &ApiClient,
    username: &str,
    password: &str,
    client_version: &str,
) -> bool {
    let mut enroll_data = ClientEnrollRequest::default();
    enroll_data.username = username.to_string();
    enroll_data.password = password.to_string();
    enroll_data.client_version = client_version.to_string();

    let response = api_client
        .post::<BasicTaskResponse, ClientEnrollRequest>("/client/auth/enroll", &enroll_data)
        .await;

    match response {
        Ok(_) => {
            info!("Enrollment successful");
            true
        }
        Err(e) => {
            error!("Failed to enroll client: {e}");
            false
        }
    }
}

pub async fn login(api_client: &ApiClient, username: &str, password: &str) -> bool {
    let mut login_data = ClientLoginRequest::default();
    login_data.username = username.to_string();
    login_data.password = password.to_string();

    let response = api_client
        .post::<TokenResponse, ClientLoginRequest>("/client/auth/login", &login_data)
        .await;

    match response {
        Ok(_) => {
            info!("Login successful");
            true
        }
        Err(e) => {
            error!("Failed to enroll client {e}");
            false
        }
    }
}

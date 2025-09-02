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
        .post::<ClientEnrollRequest, BasicTaskResponse>("/client/auth/enroll", &enroll_data)
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

pub async fn login(api_client: &mut ApiClient, username: &str, password: &str) -> bool {
    let mut login_data = ClientLoginRequest::default();
    login_data.username = username.to_string();
    login_data.password = password.to_string();

    let response = api_client
        .post::<ClientLoginRequest, TokenResponse>("/client/auth/login", &login_data)
        .await;

    match response {
        Ok(token) => {
            api_client.set_access_token(&token.access_token);
            info!("Login successful");
            true
        }
        Err(e) => {
            error!("Client login failed: {e}");
            false
        }
    }
}

pub async fn refresh_access_token(api_client: &mut ApiClient) -> bool {
    let response = api_client
        .post::<(), TokenResponse>("/client/auth/refresh", &())
        .await;

    match response {
        Ok(token) => {
            api_client.set_access_token(&token.access_token);
            info!("Refresh success");
            true
        }

        Err(e) => {
            error!("Failed to refresh access token: {e}");
            false
        }
    }
}

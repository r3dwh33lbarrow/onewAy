use crate::http::api_client::ApiClient;
use crate::schemas::auth::{ClientLoginRequest, TokenResponse};
use crate::{error, info};
use std::sync::Arc;
use tokio::sync::Mutex;

pub async fn login(api_client: Arc<Mutex<ApiClient>>, username: &str, password: &str) -> bool {
    let mut login_data = ClientLoginRequest::default();
    login_data.username = username.to_string();
    login_data.password = password.to_string();

    let mut api_client = api_client.lock().await;
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

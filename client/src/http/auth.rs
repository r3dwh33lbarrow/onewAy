use crate::http::api_client::ApiClient;
use crate::{error, info};
use crate::schemas::auth::{ClientLoginRequest, TokenResponse};

pub async fn enroll(api_client: &ApiClient, username: &str, password: &str) -> bool {
    let mut login_data = ClientLoginRequest::default();
    login_data.username = username.to_string();
    login_data.password = password.to_string();

    let response = api_client
        .post::<TokenResponse, ClientLoginRequest>("/client/auth/login", &login_data)
        .await;

    match response {
        Ok(_) => {
            info!("Enrollment successful");
            true
        },
        Err(e) => {
            error!("Failed to enroll client: {e}");
            false
        }
    }
}
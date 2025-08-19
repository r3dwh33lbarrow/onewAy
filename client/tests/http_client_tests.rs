#[cfg(test)]
mod tests {
    use client::http::api_client::ApiClient;
    use client::schemas::{BasicTaskResponse, RootResponse};
    use client::schemas::auth::{ClientEnrollRequest, ClientLoginRequest, TokenResponse};

    #[tokio::test]
    async fn test_root() {
        let api_client = ApiClient::new("http://127.0.0.1:8000/")
            .expect("failed to create API client");

        let response = api_client.get::<RootResponse>("/")
            .await
            .expect("failed to get /");

        assert_eq!(response.message, "onewAy API")
    }

    #[tokio::test]
    async fn test_enroll_then_login() {
        let api_client = ApiClient::new("http://127.0.0.1:8000/")
            .expect("failed to create API client");

        // Enroll
        let mut enrollment_data = ClientEnrollRequest::default();
        enrollment_data.username = String::from("testclient");
        enrollment_data.password = String::from("supersecretpass");
        enrollment_data.client_version = String::from("0.1.0");

        let enroll_response = api_client.post::<BasicTaskResponse, ClientEnrollRequest>("/client/auth/enroll", &enrollment_data)
            .await
            .expect("failed to post /client/auth/enroll");
        assert_eq!(enroll_response.result, "success");

        // Login
        let mut login_data = ClientLoginRequest::default();
        login_data.username = String::from("testclient");
        login_data.password = String::from("supersecretpass");

        let login_response = api_client.post::<TokenResponse, ClientLoginRequest>("/client/auth/login", &login_data)
            .await
            .expect("failed to post /client/auth/login");
        assert!(login_response.access_token.is_empty())
    }
}
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

        let mut enrollment_data = ClientEnrollRequest::default();
        enrollment_data.username = String::from("testclient");
        enrollment_data.password = String::from("supersecretpass");
        enrollment_data.client_version = String::from("TESTING");

        let enroll_response = api_client.post::<BasicTaskResponse, ClientEnrollRequest>("/client/auth/enroll", &enrollment_data)
            .await
            .expect("failed to post /client/auth/enroll");
        assert_eq!(enroll_response.result, "success");

        let mut login_data = ClientLoginRequest::default();
        login_data.username = String::from("testclient");
        login_data.password = String::from("supersecretpass");

        let login_response = api_client.post::<TokenResponse, ClientLoginRequest>("/client/auth/login", &login_data)
            .await
            .expect("failed to post /client/auth/login");
        assert!(!login_response.access_token.is_empty())
    }

    #[tokio::test]
    async fn test_double_enroll() {
        let api_client = ApiClient::new("http://127.0.0.1:8000/")
            .expect("failed to create API client");

        let mut enrollment_data_1 = ClientEnrollRequest::default();
        enrollment_data_1.username = String::from("testclient2");
        enrollment_data_1.password = String::from("secret2");
        enrollment_data_1.client_version = String::from("TESTING");
        let mut enrollment_data_2 = ClientEnrollRequest::default();
        enrollment_data_2.username = String::from("testclient2");
        enrollment_data_2.password = String::from("different-pass");
        enrollment_data_2.client_version = String::from("TESTING");

        let login_response_1 = api_client.post::<BasicTaskResponse, ClientEnrollRequest>("/client/auth/enroll", &enrollment_data_1)
            .await
            .expect("failed to post /client/auth/login");
        assert_eq!(login_response_1.result, "success");

        let login_response_2 = api_client.post::<BasicTaskResponse, ClientEnrollRequest>("/client/auth/enroll", &enrollment_data_2)
            .await;

        assert!(login_response_2.is_err(), "Expected error on double enroll, but got Ok");
    }
}
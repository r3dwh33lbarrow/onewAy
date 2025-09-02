use anyhow::{Context, Result};
use reqwest::{Client, Method, Url, header::{HeaderMap, HeaderValue, AUTHORIZATION}};
use serde::Serialize;
use serde::de::DeserializeOwned;
use std::time::Duration;
use crate::schemas::{ApiError, ApiErrorResponse};
use serde_json; // Import serde_json for JSON parsing of error responses

#[derive(Debug, Clone)]
pub struct ApiClient {
    base_url: Url,
    access_token: Option<String>,
    client: Client,
}

impl ApiClient {
    pub fn new(base_url: &str) -> Result<Self> {
        let url = Url::parse(base_url).context("invalid base URL")?;
        let client = Client::builder()
            .user_agent("oneway-api-client/0.1.0")
            .cookie_store(true)
            .timeout(Duration::from_secs(5))
            .tcp_keepalive(Duration::from_secs(30))
            .build()
            .context("failed to build reqwest client")?;

        Ok(Self {
            base_url: url,
            access_token: None,
            client,
        })
    }

    fn parse_endpoint(&self, path: &str) -> Result<Url> {
        let mut base_clone = self.base_url.clone();
        let path = path.strip_prefix('/').unwrap_or(path);
        base_clone
            .path_segments_mut()
            .map_err(|_| anyhow::anyhow!("base URL cannot be a base for paths"))?
            .extend(path.split('/').filter(|s| !s.is_empty()));
        Ok(base_clone)
    }

    fn build_headers(&self) -> HeaderMap {
        let mut headers = HeaderMap::new();

        if let Some(token) = &self.access_token {
            if let Ok(auth_value) = HeaderValue::from_str(&format!("Bearer {}", token)) {
                headers.insert(AUTHORIZATION, auth_value);
            }
        }

        headers
    }

    async fn request<Request, Response>(
        &self,
        method: Method,
        endpoint: &str,
        body: Option<&Request>,
    ) -> Result<Response>
    where
        Request: Serialize + ?Sized,
        Response: DeserializeOwned,
    {
        let url = self.parse_endpoint(endpoint)?;
        let mut request = self.client.request(method, url);

        request = request.headers(self.build_headers());

        if let Some(b) = body {
            request = request.json(b);
        }

        let response = request.send().await.context("request failed")?;

        // Check if the response is successful
        if response.status().is_success() {
            let data = response
                .json::<Response>()
                .await
                .context("failed to parse JSON response")?;
            Ok(data)
        } else {
            // Try to parse the error response to get detailed error information
            let status_code = response.status().as_u16();
            let error_text = response.text().await.context("failed to read error response")?;

            // Try to parse as structured API error first
            if let Ok(api_error) = serde_json::from_str::<ApiErrorResponse>(&error_text) {
                return Err(anyhow::Error::new(ApiError {
                    status_code,
                    detail: api_error.detail,
                }));
            }

            // Fall back to raw error text if JSON parsing fails
            Err(anyhow::Error::new(ApiError {
                status_code,
                detail: error_text,
            }))
        }
    }

    pub async fn get<T>(&self, endpoint: &str) -> Result<T>
    where
        T: DeserializeOwned,
    {
        self.request(Method::GET, endpoint, Option::<&()>::None).await
    }

    pub async fn post<Request, Response>(&self, endpoint: &str, body: &Request) -> Result<Response>
    where
        Request: Serialize + ?Sized,
        Response: DeserializeOwned,
    {
        self.request(Method::POST, endpoint, Some(body)).await
    }

    pub async fn put<Request, Response>(&self, endpoint: &str, body: &Request) -> Result<Response>
    where
        Request: Serialize + ?Sized,
        Response: DeserializeOwned,
    {
        self.request(Method::PUT, endpoint, Some(body)).await
    }

    pub async fn get_text(&self, endpoint: &str) -> Result<String> {
        let url = self.parse_endpoint(endpoint)?;
        let request = self.client.get(url).headers(self.build_headers());

        let response = request.send().await.context("request failed")?;

        if response.status().is_success() {
            let body = response.text().await.context("failed to read response text")?;
            Ok(body)
        } else {
            let status_code = response.status().as_u16();
            let error_text = response.text().await.context("failed to read error response")?;

            if let Ok(api_error) = serde_json::from_str::<ApiErrorResponse>(&error_text) {
                return Err(anyhow::Error::new(ApiError {
                    status_code,
                    detail: api_error.detail,
                }));
            }

            Err(anyhow::Error::new(ApiError {
                status_code,
                detail: error_text,
            }))
        }
    }

    pub fn set_access_token(&mut self, token: &str) {
        self.access_token = Some(token.to_string());
    }
}
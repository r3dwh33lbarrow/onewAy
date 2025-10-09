use crate::schemas::{ApiError, ApiErrorResponse};
use anyhow::Context;
use reqwest::header::{HeaderMap, HeaderValue, AUTHORIZATION};
use reqwest::{Client, Method};
use serde::de::DeserializeOwned;
use serde::Serialize;
use std::path::PathBuf;
use std::time::Duration;
use url::Url;

#[derive(Debug, Clone)]
pub struct ApiClient {
    base_url: Url,
    access_token: Option<String>,
    client: Client,
}

impl ApiClient {
    pub fn new(base_url: &str) -> anyhow::Result<Self> {
        let url = Url::parse(base_url)?;
        let client = Client::builder()
            .user_agent("oneway-api-client/0.1.0")
            .cookie_store(true)
            .timeout(Duration::from_secs(5))
            .tcp_keepalive(Duration::from_secs(30))
            .build()?;

        Ok(Self {
            base_url: url,
            access_token: None,
            client,
        })
    }

    pub fn set_access_token(&mut self, token: &str) {
        self.access_token = Some(token.to_string());
    }

    pub async fn get<T>(&self, endpoint: &str) -> anyhow::Result<T>
    where
        T: DeserializeOwned,
    {
        self.request(Method::GET, endpoint, Option::<&()>::None)
            .await
    }

    pub async fn post<Request, Response>(
        &self,
        endpoint: &str,
        body: &Request,
    ) -> anyhow::Result<Response>
    where
        Request: Serialize + ?Sized,
        Response: DeserializeOwned,
    {
        self.request(Method::POST, endpoint, Some(body)).await
    }

    pub async fn put<Request, Response>(
        &self,
        endpoint: &str,
        body: &Request,
    ) -> anyhow::Result<Response>
    where
        Request: Serialize + ?Sized,
        Response: DeserializeOwned,
    {
        self.request(Method::PUT, endpoint, Some(body)).await
    }

    pub async fn get_text(&self, endpoint: &str) -> anyhow::Result<String> {
        let url = self.parse_endpoint(endpoint)?;
        let request = self.client.get(url).headers(self.build_headers());
        let response = request.send().await.context("request failed")?;
        self.handle_text(response).await
    }

    pub async fn get_file(&self, endpoint: &str, path: &PathBuf) -> anyhow::Result<()> {
        let url = self.parse_endpoint(endpoint)?;
        let request = self.client.get(url).headers(self.build_headers());
        let response = request.send().await.context("request failed")?;
        self.handle_file(response, path).await
    }

    async fn request<Request, Response>(
        &self,
        method: Method,
        endpoint: &str,
        body: Option<&Request>,
    ) -> anyhow::Result<Response>
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
        self.handle_response(response).await
    }

    async fn handle_response<Response>(
        &self,
        response: reqwest::Response,
    ) -> anyhow::Result<Response>
    where
        Response: DeserializeOwned,
    {
        if response.status().is_success() {
            let data = response
                .json::<Response>()
                .await
                .context("failed to parse JSON response")?;
            Ok(data)
        } else {
            self.parse_error(response).await
        }
    }

    async fn handle_text(&self, response: reqwest::Response) -> anyhow::Result<String> {
        if response.status().is_success() {
            let body = response
                .text()
                .await
                .context("failed to read response text")?;
            Ok(body)
        } else {
            self.parse_error(response).await
        }
    }

    async fn handle_file(&self, response: reqwest::Response, path: &PathBuf) -> anyhow::Result<()> {
        if response.status().is_success() {
            let bytes = response
                .bytes()
                .await
                .context("failed to read response bytes")?;
            std::fs::write(path, bytes).context("failed to write file")?;
            Ok(())
        } else {
            self.parse_error(response).await
        }
    }

    async fn parse_error<T>(&self, response: reqwest::Response) -> anyhow::Result<T> {
        let status_code = response.status().as_u16();
        let error_text = response
            .text()
            .await
            .context("failed to read error response")?;

        if let Ok(api_error) = serde_json::from_str::<ApiErrorResponse>(&error_text) {
            Err(anyhow::Error::new(ApiError {
                status_code,
                detail: api_error.detail,
            }))
        } else {
            Err(anyhow::Error::new(ApiError {
                status_code,
                detail: error_text,
            }))
        }
    }

    fn parse_endpoint(&self, path: &str) -> anyhow::Result<Url> {
        let mut base_clone = self.base_url.clone();
        let path = path.strip_prefix('/').unwrap_or(path);
        base_clone
            .path_segments_mut()
            .map_err(|_| anyhow::anyhow!("base URL failed to map"))?
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
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_endpoint() {
        let api = ApiClient::new("http://localhost:8000/").unwrap();
        let u = api.parse_endpoint("/client/me").unwrap();
        assert_eq!(u.as_str(), "http://localhost:8000/client/me");

        let u2 = api.parse_endpoint("client/me").unwrap();
        assert_eq!(u2.as_str(), "http://localhost:8000/client/me");
    }

    #[test]
    fn test_build_headers_with_token() {
        let mut api = ApiClient::new("http://localhost:8000/").unwrap();
        api.set_access_token("abc123");
        let headers = api.build_headers();
        let v = headers.get(AUTHORIZATION).unwrap();
        assert_eq!(v.to_str().unwrap(), "Bearer abc123");
    }

    #[test]
    fn test_build_headers_without_token() {
        let api = ApiClient::new("http://localhost:8000/").unwrap();
        let headers = api.build_headers();
        assert!(headers.get(AUTHORIZATION).is_none());
    }
}

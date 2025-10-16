use crate::schemas::{ApiError, ApiErrorResponse};
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

    pub async fn get<T>(&self, endpoint: &str) -> Result<T, ApiError>
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
    ) -> Result<Response, ApiError>
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
    ) -> Result<Response, ApiError>
    where
        Request: Serialize + ?Sized,
        Response: DeserializeOwned,
    {
        self.request(Method::PUT, endpoint, Some(body)).await
    }

    pub async fn get_text(&self, endpoint: &str) -> Result<String, ApiError> {
        let url = self.parse_endpoint(endpoint)?;
        let request = self.client.get(url).headers(self.build_headers());
        let response = request.send().await.map_err(|err| self.map_request_error(err))?;
        self.handle_text(response).await
    }

    pub async fn get_file(&self, endpoint: &str, path: &PathBuf) -> Result<(), ApiError> {
        let url = self.parse_endpoint(endpoint)?;
        let request = self.client.get(url).headers(self.build_headers());
        let response = request.send().await.map_err(|err| self.map_request_error(err))?;
        self.handle_file(response, path).await
    }

    async fn request<Request, Response>(
        &self,
        method: Method,
        endpoint: &str,
        body: Option<&Request>,
    ) -> Result<Response, ApiError>
    where
        Request: Serialize + ?Sized,
        Response: DeserializeOwned,
    {
        let url = self.parse_endpoint(endpoint).map_err(|_| ApiError {
            status_code: -1,
            detail: "Failed to parse URL".to_string(),
        })?;
        let mut request = self.client.request(method, url);
        request = request.headers(self.build_headers());

        if let Some(b) = body {
            request = request.json(b);
        }

        let response = request.send().await.map_err(|err| self.map_request_error(err))?;
        self.handle_response(response).await
    }

    async fn handle_response<Response>(
        &self,
        response: reqwest::Response,
    ) -> Result<Response, ApiError>
    where
        Response: DeserializeOwned,
    {
        if response.status().is_success() {
            let status_code = response.status().as_u16() as i32;
            let data = response
                .json::<Response>()
                .await
                .map_err(|_| ApiError {
                    status_code,
                    detail: "Could not parse JSON".to_string(),
                })?;
            Ok(data)
        } else {
            Err(self.parse_error(response).await)
        }
    }

    async fn handle_text(&self, response: reqwest::Response) -> Result<String, ApiError> {
        if response.status().is_success() {
            let body = response
                .text()
                .await
                .map_err(|_| ApiError {
                    status_code: -1,
                    detail: "Failed to read response text".to_string(),
                })?;
            Ok(body)
        } else {
            Err(self.parse_error(response).await)
        }
    }

    async fn handle_file(&self, response: reqwest::Response, path: &PathBuf) -> Result<(), ApiError> {
        if response.status().is_success() {
            let bytes = response
                .bytes()
                .await
                .map_err(|_| ApiError {
                    status_code: -1,
                    detail: "Failed to read response bytes".to_string(),
                })?;
            std::fs::write(path, bytes).map_err(|_| ApiError {
                status_code: -1,
                detail: "Failed to write file".to_string(),
            })?;
            Ok(())
        } else {
            Err(self.parse_error(response).await)
        }
    }

    pub async fn post_with_query<Request, Response>(
        &self,
        endpoint: &str,
        query: &[(&str, &str)],
        body: &Request,
    ) -> Result<Response, ApiError>
    where
        Request: Serialize + ?Sized,
        Response: DeserializeOwned,
    {
        let mut url = self.parse_endpoint(endpoint)?;
        url.query_pairs_mut().extend_pairs(query);
        let mut request = self.client.request(Method::POST, url);
        request = request.headers(self.build_headers()).json(body);
        let response = request.send().await.map_err(|err| self.map_request_error(err))?;
        self.handle_response(response).await
    }
    
    pub async fn put_with_query<Request, Response>(
        &self,
        endpoint: &str,
        query: &[(&str, &str)],
        body: &Request,
    ) -> Result<Response, ApiError>
    where
        Request: Serialize + ?Sized,
        Response: DeserializeOwned,
    {
        let mut url = self.parse_endpoint(endpoint)?;
        url.query_pairs_mut().extend_pairs(query);
        let mut request = self.client.request(Method::PUT, url);
        request = request.headers(self.build_headers()).json(body);
        let response = request.send().await.map_err(|err| self.map_request_error(err))?;
        self.handle_response(response).await
    }

    async fn parse_error(&self, response: reqwest::Response) -> ApiError {
        let status_code = response.status().as_u16();
        let error_text = response
            .text()
            .await
            .map_err(|_| ApiError {
                status_code: -1,
                detail: "Failed to parse error response".to_string(),
            });

        match error_text {
            Ok(text) => {
                if let Ok(api_error) = serde_json::from_str::<ApiErrorResponse>(&text) {
                    ApiError {
                        status_code: status_code as i32,
                        detail: api_error.detail,
                    }
                } else {
                    ApiError {
                        status_code: status_code as i32,
                        detail: text,
                    }
                }
            },
            Err(e) => e,
        }
    }

    fn parse_endpoint(&self, path: &str) -> Result<Url, ApiError> {
        let mut base_clone = self.base_url.clone();
        let path = path.strip_prefix('/').unwrap_or(path);
        base_clone
            .path_segments_mut()
            .map_err(|_| ApiError {
                status_code: -1,
                detail: "Base URL failed to map".to_string(),
            })?
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

    fn map_request_error(&self, err: reqwest::Error) -> ApiError {
        ApiError {
            status_code: err.status().map(|s| s.as_u16() as i32).unwrap_or(-1),
            detail: err.to_string(),
        }
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

use anyhow::{Context, Result};
use reqwest::{Client, Method, Url};
use serde::Serialize;
use serde::de::DeserializeOwned;
use std::time::Duration;

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
            .user_agent("oneway-api-client/0.1")
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

    fn parse_path(&self, path: &str) -> Result<Url> {
        let mut base_clone = self.base_url.clone();
        let path = path.strip_prefix('/').unwrap_or(path);
        base_clone
            .path_segments_mut()
            .map_err(|_| anyhow::anyhow!("base URL cannot be a base for paths"))?
            .extend(path.split('/').filter(|s| !s.is_empty()));
        Ok(base_clone)
    }

    async fn request<TRes, TBody>(
        &self,
        method: Method,
        path: &str,
        body: Option<&TBody>,
    ) -> Result<TRes>
    where
        TRes: DeserializeOwned,
        TBody: Serialize + ?Sized,
    {
        let url = self.parse_path(path)?;
        let mut request = self.client.request(method, url);

        if let Some(b) = body {
            request = request.json(b);
        }

        let response = request.send().await.context("request failed")?;
        let response = response.error_for_status().context("non-2xx status")?;
        let data = response
            .json::<TRes>()
            .await
            .context("failed to parse JSON")?;
        Ok(data)
    }

    pub async fn get<T>(&self, path: &str) -> Result<T>
    where
        T: DeserializeOwned,
    {
        self.request(Method::GET, path, Option::<&()>::None).await
    }

    pub async fn post<TRes, TBody>(&self, path: &str, body: &TBody) -> Result<TRes>
    where
        TRes: DeserializeOwned,
        TBody: Serialize + ?Sized,
    {
        self.request(Method::POST, path, Some(body)).await
    }

    pub async fn get_text(&self, path: &str) -> Result<String> {
        let url = self.parse_path(path)?;
        let request = self.client.get(url);

        let response = request.send().await?.error_for_status()?;
        let body = response.text().await?;
        Ok(body)
    }

    pub fn set_access_token(&mut self, token_str: &str) {
        self.access_token = Some(token_str.to_string());
    }
}

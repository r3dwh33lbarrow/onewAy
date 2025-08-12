use crate::api_client::ApiClient;
mod logger;
mod api_client;

#[tokio::main]
async fn main() {
    debug!("Sending a request to http://example.com");
    let api_client = ApiClient::new("http://example.com").expect("Failed to init ApiClient");
    let text = api_client.get_text("").await.expect("Failed to get url");
    info!("{text}");
}

use std::sync::Arc;
use uuid::Uuid;

use anyhow::Result;
use client::http::api_client::ApiClient;
use client::http::auth::{login, refresh_access_token};
use client::schemas::RootResponse;
use futures_util::{SinkExt, StreamExt};
use reqwest::Client;
use serde::Deserialize;
use serde_json::json;
use serial_test::serial;
use tokio::sync::Mutex;
use tokio_tungstenite::connect_async;
use tungstenite::Message;

const BASE_URL: &str = "http://127.0.0.1:8000/";
const CLIENT_VERSION: &str = "0.0.1";

fn unique_suffix(prefix: &str) -> String {
    format!("{}_{}", prefix, Uuid::new_v4())
}

async fn ensure_user_logged_in(http: &Client, username: &str, password: &str) -> Result<()> {
    let register = http
        .post(format!("{BASE_URL}user/auth/register"))
        .json(&json!({
            "username": username,
            "password": password
        }))
        .send()
        .await?;

    if !(register.status().is_success() || register.status() == reqwest::StatusCode::CONFLICT) {
        return Err(anyhow::anyhow!(
            "failed to register helper user: {}",
            register.status()
        ));
    }

    let login = http
        .post(format!("{BASE_URL}user/auth/login"))
        .json(&json!({
            "username": username,
            "password": password
        }))
        .send()
        .await?;
    login.error_for_status_ref()?;

    Ok(())
}

async fn provision_client(username: &str, password: &str) -> Result<()> {
    let http = Client::builder()
        .cookie_store(true)
        .user_agent("integration-tests/0.1.0")
        .build()?;

    let user_username = unique_suffix("rust_user");
    let user_password = "pw123";

    ensure_user_logged_in(&http, &user_username, user_password).await?;

    let enroll = http
        .post(format!("{BASE_URL}client/auth/enroll"))
        .json(&json!({
            "username": username,
            "password": password,
            "client_version": CLIENT_VERSION
        }))
        .send()
        .await?;
    if !enroll.status().is_success() {
        let status = enroll.status();
        let body = enroll.text().await.unwrap_or_else(|_| "<no body>".into());
        return Err(anyhow::anyhow!(
            "client enroll failed: status {} ({:?}) body {body}",
            status.as_u16(),
            status
        ));
    }

    Ok(())
}

#[tokio::test]
#[serial]
async fn test_root_alive() {
    let api = ApiClient::new(BASE_URL).expect("api client");
    let response: RootResponse = api.get("/").await.expect("GET /");
    assert_eq!(response.message, "onewAy API");
}

#[derive(Debug, Deserialize)]
struct ClientMeResponse {
    username: String,
}

#[tokio::test]
#[serial]
async fn test_enroll_login_and_me() {
    let api = Arc::new(Mutex::new(ApiClient::new(BASE_URL).expect("api client")));
    let username = unique_suffix("rust_int");
    let password = "pw123";

    provision_client(&username, password)
        .await
        .expect("client provisioned");

    assert!(login(api.clone(), &username, password).await);

    let me: ClientMeResponse = api
        .lock()
        .await
        .get("/client/me")
        .await
        .expect("/client/me");
    assert_eq!(me.username, username);
}

#[tokio::test]
#[serial]
async fn test_refresh_access_token_and_me() {
    let api = Arc::new(Mutex::new(ApiClient::new(BASE_URL).expect("api client")));
    let username = unique_suffix("rust_refresh");
    let password = "pw123";

    provision_client(&username, password)
        .await
        .expect("client provisioned");
    assert!(login(api.clone(), &username, password).await);

    let refreshed = refresh_access_token(&mut *api.lock().await).await;
    assert!(refreshed, "expected refresh token to succeed");

    let me: ClientMeResponse = api
        .lock()
        .await
        .get("/client/me")
        .await
        .expect("/client/me after refresh");
    assert_eq!(me.username, username);
}

#[tokio::test]
#[serial]
async fn test_client_update_missing_binary() {
    let api = Arc::new(Mutex::new(ApiClient::new(BASE_URL).expect("api client")));
    let username = unique_suffix("rust_update");
    let password = "pw123";

    provision_client(&username, password)
        .await
        .expect("client provisioned");
    assert!(login(api.clone(), &username, password).await);

    let tmp_path = std::env::temp_dir().join(format!("{}_client_update.bin", username));
    let result = api.lock().await.get_file("/client/update", &tmp_path).await;
    assert!(result.is_err(), "expected update to fail (missing binary)");

    let err = result.err().unwrap();
    assert_eq!(err.status_code, 500);
    assert!(err.detail.contains("Unable to find client binary"));
}

#[tokio::test]
#[serial]
async fn test_ws_client_token_and_ping_pong() {
    let api = Arc::new(Mutex::new(ApiClient::new(BASE_URL).expect("api client")));
    let username = unique_suffix("rust_ws");
    let password = "pw123";

    provision_client(&username, password)
        .await
        .expect("client provisioned");
    assert!(login(api.clone(), &username, password).await);

    let token_response: serde_json::Value = api
        .lock()
        .await
        .post("/ws-client-token", &())
        .await
        .expect("ws token");
    let access_token = token_response
        .get("access_token")
        .and_then(|v| v.as_str())
        .expect("access_token present");
    let ws_url = format!("ws://127.0.0.1:8000/ws-client?token={access_token}");

    let (mut stream, _) = connect_async(ws_url).await.expect("connect ws");
    stream
        .send(Message::Text(json!({"type": "ping"}).to_string().into()))
        .await
        .expect("send ping");

    if let Some(Ok(Message::Text(text))) = stream.next().await {
        let payload: serde_json::Value = serde_json::from_str(&text).expect("json pong");
        assert_eq!(payload.get("type").and_then(|v| v.as_str()), Some("pong"));
    } else {
        panic!("expected pong text message");
    }
}

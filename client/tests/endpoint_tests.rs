use client::ApiClient;
use client::http::auth::{login, refresh_access_token};
use client::schemas::{ApiError, RootResponse};
use reqwest::Client;
use serde::Deserialize;
use serde_json::json;
use std::sync::Arc;
use tokio::sync::Mutex;
use tokio_tungstenite::connect_async;

fn base_url() -> &'static str {
    "http://127.0.0.1:8000/"
}

fn unique_username(prefix: &str) -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!("{}_{}", prefix, nanos)
}

async fn provision_client(username: &str, password: &str) -> anyhow::Result<()> {
    const CLIENT_VERSION: &str = "0.1.0";
    let http = Client::builder().cookie_store(true).build()?;

    let user_username = unique_username("rust_user");
    let user_password = "pw123";

    let register_resp = http
        .post(format!("{}user/auth/register", base_url()))
        .json(&json!({
            "username": user_username,
            "password": user_password
        }))
        .send()
        .await?;

    if !(register_resp.status().is_success()
        || register_resp.status() == reqwest::StatusCode::CONFLICT)
    {
        return Err(anyhow::anyhow!(
            "failed to register helper user: {}",
            register_resp.status()
        ));
    }

    let login_resp = http
        .post(format!("{}user/auth/login", base_url()))
        .json(&json!({
            "username": user_username,
            "password": user_password
        }))
        .send()
        .await?;
    login_resp.error_for_status_ref()?;

    let enroll_resp = http
        .post(format!("{}client/auth/enroll", base_url()))
        .json(&json!({
            "username": username,
            "password": password,
            "client_version": CLIENT_VERSION
        }))
        .send()
        .await?;
    enroll_resp.error_for_status_ref()?;

    Ok(())
}

#[tokio::test]
async fn test_root_alive() {
    let api = ApiClient::new(base_url()).expect("api client");
    let root: RootResponse = api.get("/").await.expect("GET /");
    assert_eq!(root.message, "onewAy API");
}

#[derive(Debug, Deserialize)]
struct ClientMeResponse {
    username: String,
}

#[tokio::test]
async fn test_enroll_login_and_me() {
    let api = ApiClient::new(base_url()).expect("api client");
    let api = Arc::new(Mutex::new(api));
    let username = unique_username("rust_int");
    let password = "pw123";

    provision_client(&username, password)
        .await
        .expect("client provisioned");

    let logged_in = login(api.clone(), &username, password).await;
    assert!(logged_in, "expected login to succeed");

    let me: ClientMeResponse = api
        .lock()
        .await
        .get("/client/me")
        .await
        .expect("/client/me");
    assert_eq!(me.username, username);
}

#[tokio::test]
async fn test_refresh_access_token_and_me() {
    let api = ApiClient::new(base_url()).expect("api client");
    let api = Arc::new(Mutex::new(api));
    let username = unique_username("rust_refresh");
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
async fn test_client_get_unknown_404() {
    let api = ApiClient::new(base_url()).expect("api client");
    let api = Arc::new(Mutex::new(api));
    let username = unique_username("rust_unknown");
    let password = "pw123";

    provision_client(&username, password)
        .await
        .expect("client provisioned");
    assert!(login(api.clone(), &username, password).await);

    let res: anyhow::Result<serde_json::Value> =
        api.lock().await.get("/client/get/no_such_user").await;
    assert!(res.is_err(), "expected 404 error");

    let err = res.err().unwrap();
    if let Some(api_err) = err.downcast_ref::<ApiError>() {
        assert_eq!(api_err.status_code, 404);
        assert!(api_err.detail.contains("Client not found"));
    } else {
        panic!("expected ApiError, got: {err}");
    }
}

#[tokio::test]
async fn test_client_update_missing_binary_500() {
    let api = ApiClient::new(base_url()).expect("api client");
    let api = Arc::new(Mutex::new(api));
    let username = unique_username("rust_update");
    let password = "pw123";

    provision_client(&username, password)
        .await
        .expect("client provisioned");
    assert!(login(api.clone(), &username, password).await);

    let tmp_path = std::env::temp_dir().join(format!("{}_client_update.bin", username));
    let res = api.lock().await.get_file("/client/update", &tmp_path).await;
    assert!(res.is_err(), "expected error due to missing server binary");

    let err = res.err().unwrap();
    if let Some(api_err) = err.downcast_ref::<ApiError>() {
        assert_eq!(api_err.status_code, 500);
        assert!(api_err.detail.contains("Unable to find client binary"));
    } else {
        panic!("expected ApiError, got: {err}");
    }
}

#[tokio::test]
async fn test_ws_client_token_and_ping_pong() {
    // Login as a client
    let api = ApiClient::new(base_url()).expect("api client");
    let api = Arc::new(Mutex::new(api));
    let username = unique_username("rust_ws");
    let password = "pw123";

    provision_client(&username, password)
        .await
        .expect("client provisioned");
    assert!(login(api.clone(), &username, password).await);

    let token_val: serde_json::Value = api
        .lock()
        .await
        .post("/ws-client-token", &())
        .await
        .expect("ws token");
    let access = token_val
        .get("access_token")
        .and_then(|v| v.as_str())
        .expect("access_token field present");
    let ws_url = format!("ws://127.0.0.1:8000/ws-client?token={}", access);

    let (mut stream, _) = connect_async(ws_url).await.expect("connect ws");
    let msg = serde_json::json!({"type": "ping"}).to_string();
    use futures_util::{SinkExt, StreamExt};
    use tungstenite::Message;

    stream
        .send(Message::Text(msg.into()))
        .await
        .expect("send ping");
    if let Some(Ok(Message::Text(txt))) = stream.next().await {
        let v: serde_json::Value = serde_json::from_str(&txt).expect("json pong");
        assert_eq!(v.get("type").and_then(|x| x.as_str()), Some("pong"));
    } else {
        panic!("expected pong text message");
    }
}

use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use tokio_tungstenite::{connect_async, tungstenite::Message};
use anyhow::Result;
use crate::http::api_client::ApiClient;
use crate::info;

#[derive(Debug, Serialize, Deserialize)]
struct WebsocketMessage {
    message_type: String,
    module_name: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct AccessTokenResponse {
    access_token: String,
    token_type: String,
}

pub async fn start_websocket_client(url: &str, api_client: &ApiClient) -> Result<()> {
    // Get websocket token from API
    let access_token = api_client.post::<(), AccessTokenResponse>("/ws-client-token", &()).await?;
    let access_token = access_token.access_token;
    
    let url = url.to_owned() + "?token=" + &access_token;

    let (ws_stream, _) = connect_async(url)
        .await
        .map_err(|e| anyhow::anyhow!("Failed to connect to websocket: {}", e))?;

    let (mut write, mut read) = ws_stream.split();

    println!("WebSocket connection established");

    while let Some(message) = read.next().await {
        match message {
            Ok(Message::Text(text)) => {
                // Try to parse the JSON message into our WebsocketMessage struct
                match serde_json::from_str::<WebsocketMessage>(&text) {
                    Ok(ws_msg) => {
                        println!("Received message: {:?}", ws_msg);
                        // Handle the parsed message here
                        handle_websocket_message(ws_msg).await;
                    }
                    Err(e) => {
                        eprintln!("Failed to parse message as JSON: {}. Raw message: {}", e, text);
                    }
                }
            }
            Ok(Message::Binary(data)) => {
                println!("Received binary message: {} bytes", data.len());
                // Handle binary data if needed
            }
            Ok(Message::Close(frame)) => {
                println!("WebSocket connection closed: {:?}", frame);
                break;
            }
            Ok(Message::Ping(data)) => {
                println!("Received ping, sending pong");
                if let Err(e) = write.send(Message::Pong(data)).await {
                    eprintln!("Failed to send pong: {}", e);
                }
            }
            Ok(Message::Pong(_)) => {
                println!("Received pong");
            }
            Ok(Message::Frame(_)) => {
                // Raw frames are typically handled internally
            }
            Err(e) => {
                eprintln!("WebSocket error: {}", e);
                break;
            }
        }
    }

    println!("WebSocket client stopped");
    Ok(())
}

async fn handle_websocket_message(message: WebsocketMessage) {
    match message.message_type.as_str() {
        "module_run" => {
            info!("Running module: {}", message.module_name);
        }
        _ => {
            println!("Unknown message type: {} for module: {}", message.message_type, message.module_name);
        }
    }
}
use crate::http::api_client::ApiClient;
use crate::info;
use crate::module_manager::ModuleManager;
use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::mpsc::{UnboundedReceiver, UnboundedSender, unbounded_channel};
use tokio_tungstenite::tungstenite::Bytes;
use tokio_tungstenite::{connect_async, tungstenite::Message};

pub enum OutgoingMessage {
    Text(String),
    Pong(Bytes),
}

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

pub async fn start_websocket_client(
    url: &str,
    api_client: &ApiClient,
    module_manager: Arc<ModuleManager>,
) -> Result<()> {
    // Get websocket token from API
    let access_token = api_client
        .post::<(), AccessTokenResponse>("/ws-client-token", &())
        .await?;
    let access_token = access_token.access_token;

    let url = url.to_owned() + "?token=" + &access_token;

    let (ws_stream, _) = connect_async(url)
        .await
        .map_err(|e| anyhow::anyhow!("Failed to connect to websocket: {}", e))?;

    let (mut write, mut read) = ws_stream.split();

    // Writer task and channels
    let (tx, mut rx): (
        UnboundedSender<OutgoingMessage>,
        UnboundedReceiver<OutgoingMessage>,
    ) = unbounded_channel();
    tokio::spawn(async move {
        while let Some(msg) = rx.recv().await {
            let send_res = match msg {
                OutgoingMessage::Text(txt) => write.send(Message::Text(txt.into())).await,
                OutgoingMessage::Pong(data) => write.send(Message::Pong(data)).await,
            };
            if let Err(e) = send_res {
                eprintln!("Failed to send message over WebSocket: {}", e);
                break;
            }
        }
    });

    // Text forwarding channel for module manager
    let (text_tx, mut text_rx) = unbounded_channel::<String>();
    let tx_clone_for_forward = tx.clone();
    tokio::spawn(async move {
        while let Some(s) = text_rx.recv().await {
            let _ = tx_clone_for_forward.send(OutgoingMessage::Text(s));
        }
    });

    println!("WebSocket connection established");

    while let Some(message) = read.next().await {
        match message {
            Ok(Message::Text(text)) => {
                // Try to parse the JSON message into our WebsocketMessage struct
                match serde_json::from_str::<WebsocketMessage>(&text) {
                    Ok(ws_msg) => {
                        println!("Received message: {:?}", ws_msg);
                        // Handle the parsed message here
                        handle_websocket_message(
                            ws_msg,
                            Arc::clone(&module_manager),
                            text_tx.clone(),
                        )
                        .await;
                    }
                    Err(e) => {
                        eprintln!(
                            "Failed to parse message as JSON: {}. Raw message: {}",
                            e, text
                        );
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
                let _ = tx.send(OutgoingMessage::Pong(data));
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

async fn handle_websocket_message(
    message: WebsocketMessage,
    module_manager: Arc<ModuleManager>,
    tx: UnboundedSender<String>,
) {
    match message.message_type.as_str() {
        "module_run" => {
            info!("Running module: {}", message.module_name);
            let module = module_manager.get_module(&*message.module_name).await;
            if module.is_none() {
                println!("Module {} not found", message.module_name);
                return;
            }

            // Start and stream output back to server
            if let Err(e) = module_manager
                .start_module_streaming(&message.module_name, tx.clone())
                .await
            {
                eprintln!(
                    "Failed to run and stream module {}: {}",
                    message.module_name, e
                );
            }
        }
        "module_cancel" => {
            info!("Cancel requested for module: {}", message.module_name);
            match module_manager.cancel_module(&message.module_name).await {
                Ok(true) => {
                    let _ = tx.send(
                        serde_json::json!({
                            "message_type": "module_canceled",
                            "module_name": message.module_name
                        })
                        .to_string(),
                    );
                }
                Ok(false) => {
                    // Not running; optionally emit an event
                }
                Err(e) => {
                    eprintln!("Failed to cancel module {}: {}", message.module_name, e);
                }
            }
        }
        _ => {
            println!(
                "Unknown message type: {} for module: {}",
                message.message_type, message.module_name
            );
        }
    }
}

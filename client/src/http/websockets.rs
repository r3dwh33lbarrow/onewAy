use crate::http::api_client::ApiClient;
use crate::module_manager::ModuleManager;
use crate::schemas::websockets::*;
use crate::warn;
use crate::{debug, error, info};
use futures_util::{SinkExt, StreamExt};
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::sync::mpsc::{UnboundedReceiver, UnboundedSender, unbounded_channel};
use tokio::sync::Mutex;
use tokio_tungstenite::connect_async;
use tokio_tungstenite::tungstenite::Bytes;
use tungstenite::Message;

pub enum OutgoingMessage {
    Text(String),
    Pong(Bytes),
}

pub async fn start_websocket_client(
    url: &str,
    api_client: Arc<Mutex<ApiClient>>,
    module_manager: Arc<ModuleManager>,
) -> anyhow::Result<()> {
    let api_client = api_client.lock().await;
    let access_token = api_client
        .post::<(), AccessTokenResponse>("/ws-client-token", &())
        .await?;
    let access_token = access_token.access_token;
    let url = url.to_owned() + "?token=" + &access_token;
    let (ws_stream, _) = connect_async(url).await?;
    let (mut write, mut read) = ws_stream.split();
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
                error!("Failed to send message over Websocket: {}", e);
                break;
            }
        }
    });

    let (text_tx, mut text_rx) = unbounded_channel::<String>();
    let tx_clone_for_forward = tx.clone();
    tokio::spawn(async move {
        while let Some(s) = text_rx.recv().await {
            let _ = tx_clone_for_forward.send(OutgoingMessage::Text(s));
        }
    });

    info!("WebSocket connection established");

    while let Some(message) = read.next().await {
        match message {
            Ok(Message::Text(text)) => match serde_json::from_str::<WebsocketMessage>(&text) {
                Ok(ws_msg) => {
                    debug!("Received message: {:?}", ws_msg);
                    handle_websocket_message(ws_msg, Arc::clone(&module_manager), text_tx.clone())
                        .await;
                }

                Err(e) => {
                    error!(
                        "Failed to parse message as JSON: {}. Raw message: {}",
                        e, text
                    );
                }
            },

            Ok(Message::Binary(data)) => {
                info!("Received binary message: {} bytes", data.len());
            }
            Ok(Message::Close(frame)) => {
                info!("WebSocket connection closed: {:?}", frame);
                break;
            }
            Ok(Message::Ping(data)) => {
                debug!("Received ping, sending pong");
                let _ = tx.send(OutgoingMessage::Pong(data));
            }
            Ok(Message::Pong(_)) => {
                debug!("Received pong");
            }
            Ok(Message::Frame(_)) => {}
            Err(e) => {
                error!("WebSocket error: {}", e);
                break;
            }
        }
    }

    debug!("WebSocket client stopped");
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
                error!("Module {} not found", message.module_name);
                return;
            }

            // Start the module and get the streams
            let streams = match module_manager
                .start_module_streaming(&message.module_name)
                .await
            {
                Ok(s) => s,
                Err(e) => {
                    error!(
                        "Failed to run and stream module {}: {}",
                        message.module_name, e
                    );
                    return;
                }
            };

            let _ = tx.send(
                serde_json::json!({
                    "message_type": "module_started",
                    "module_name": message.module_name
                })
                    .to_string(),
            );

            {
                let tx_clone = tx.clone();
                let module_name = message.module_name.clone();
                let stdout = streams.stdout;

                tokio::spawn(async move {
                    let mut reader = BufReader::new(stdout).lines();
                    while let Ok(Some(line)) = reader.next_line().await {
                        let _ = tx_clone.send(
                            serde_json::json!({
                                "message_type": "module_output",
                                "module_name": module_name,
                                "stream": "stdout",
                                "line": line
                            })
                                .to_string(),
                        );
                    }
                });
            }

            {
                let tx_clone = tx.clone();
                let module_name = message.module_name.clone();
                let stderr = streams.stderr;

                tokio::spawn(async move {
                    let mut reader = BufReader::new(stderr).lines();
                    while let Ok(Some(line)) = reader.next_line().await {
                        let _ = tx_clone.send(
                            serde_json::json!({
                                "message_type": "module_output",
                                "module_name": module_name,
                                "stream": "stderr",
                                "line": line
                            })
                                .to_string(),
                        );
                    }
                });
            }
        }
        "module_cancel" => {
            info!("Cancel requested for module: {}", message.module_name);
            if module_manager.cancel_module(&message.module_name).await {
                let _ = tx.send(
                    serde_json::json!({
                        "message_type": "module_canceled",
                        "module_name": message.module_name
                    })
                        .to_string(),
                );
            }
        }
        _ => {
            warn!(
                "Unknown message type: {} for module: {}",
                message.message_type, message.module_name
            );
        }
    }
}
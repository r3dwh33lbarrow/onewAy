use crate::http::api_client::ApiClient;
use crate::module_manager::ModuleManager;
use crate::schemas::websockets;
use crate::schemas::websockets::*;
use crate::{debug, error, info};
use futures_util::{SinkExt, StreamExt};
use std::sync::Arc;
use tokio::sync::Mutex;
use tokio::sync::mpsc::{UnboundedReceiver, UnboundedSender, unbounded_channel};
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
    let access_token = {
        let api_client = api_client.lock().await;
        let access_token = api_client
            .post::<(), AccessTokenResponse>("/ws-client-token", &())
            .await?;
        access_token.access_token
    };
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
            Ok(Message::Text(text)) => match serde_json::from_str::<websockets::Message>(&text) {
                Ok(ws_msg) => {
                    debug!("Received message: {:?}", ws_msg);
                    handle_websocket_message(
                        ws_msg,
                        Arc::clone(&module_manager),
                        text_tx.clone(),
                        Arc::clone(&api_client),
                    )
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
    message: websockets::Message,
    module_manager: Arc<ModuleManager>,
    tx: UnboundedSender<String>,
    api_client: Arc<Mutex<ApiClient>>,
) {
    match message {
        websockets::Message::ModuleRun { from: _, module } => {
            let module_name = module.name.clone();
            info!("Running module: {}", module_name);
            let module_opt = module_manager.get_module(&module_name).await;
            if module_opt.is_none() {
                error!("Module {} not found", module_name);
                let _ = tx.send(
                    serde_json::json!({
                        "type": "error",
                        "message": format!("Module {} not found", module_name),
                    })
                    .to_string(),
                );
                return;
            }

            if let Err(e) = module_manager
                .start_module_streaming(&module_name, tx.clone(), api_client)
                .await
            {
                error!("Failed to start module streaming: {}", e.to_string());
                let _ = tx.send(
                    serde_json::json!({
                        "type": "error",
                        "message": format!("Failed to start module streaming for {}", module_name),
                    })
                    .to_string(),
                );
                return;
            }
        }
        websockets::Message::ModuleStdin { from: _, stdin } => {
            let result = module_manager
                .give_to_stdin(&stdin.module_name, stdin.data.as_slice())
                .await;
            if let Err(err) = result {
                error!("Failed to send to stdin: {}", err.to_string());
                let _ = tx.send(
                    serde_json::json!({
                        "type": "error",
                        "message": format!("Failed to write to stdin for {}: {}", stdin.module_name, err.to_string()),
                    })
                    .to_string(),
                );
            }
        }
        websockets::Message::ModuleCancel { from: _, event } => {
            info!("Cancel requested for module: {}", event.module_name);
            if module_manager.cancel_module(&event.module_name).await {
                let _ = tx.send(
                    serde_json::json!({
                        "type": "module_canceled",
                        "from": "client",
                        "event": {
                            "module_name": event.module_name,
                            "code": "canceled"
                        }
                    })
                    .to_string(),
                );
            }
        }
    }
}

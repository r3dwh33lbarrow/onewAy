import asyncio
import json
from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.logger import get_logger
from app.models.client import Client
from app.models.user import User
from app.schemas.general import TokenResponse
from app.services.authentication import (
    TokenType,
    create_access_token,
    get_current_client,
    get_current_user,
    verify_websocket_access_token,
)
from app.services.client_websockets import client_websocket_manager
from app.services.user_websockets import user_websocket_manager

CLIENT_WEBSOCKET_HEARTBEAT_SECONDS = 60
CLIENT_WEBSOCKET_PONG_TIMEOUT_SECONDS = 10

router = APIRouter()
logger = get_logger()


async def _update_client_alive_status(
    db: AsyncSession, client: Client, *, alive: bool
) -> None:
    client.alive = alive
    client.last_contact = datetime.now(UTC)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(
            "Failed to update alive status for client '%s'", client.username
        )


@router.websocket("/ws-user")
async def websocket_user_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for user connections.

    Handles WebSocket connections from users, managing connection lifecycle
    and responding to ping messages to maintain connection health.

    Args:
        websocket: WebSocket connection instance
        token: Authentication token for user verification
        db: For checking if the client is running

    Raises:
        WebSocketException: 401 if token is invalid
        WebSocketException: 500 for server errors
    """
    try:
        user_uuid = verify_websocket_access_token(token)
        user = await db.execute(select(User).where(User.uuid == user_uuid))
        user = user.scalar_one_or_none()
        if not user:
            await websocket.close(401, "User does not exist")
            return

        logger.info("User websocket connected: %s", user_uuid)
        await user_websocket_manager.connect(websocket, user_uuid)

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                message_type = message.get("type")
                if message_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message_type == "module_stdin":
                    stdin = message.get("stdin")
                    if not stdin:
                        error_text = "No stdin json data specified for module_stdin"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    module_name = stdin.get("module_name")
                    data_value = stdin.get("data")

                    if not module_name:
                        error_text = "No module_name specified for module_stdin"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    if data_value is None:
                        error_text = "No data specified for module_stdin"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    # Accept either a string (UTF-8) or an array of numbers
                    if isinstance(data_value, str):
                        data_bytes = list(data_value.encode("utf-8"))
                    elif isinstance(data_value, list) and all(
                        isinstance(x, int) and 0 <= x <= 255 for x in data_value
                    ):
                        data_bytes = data_value
                    else:
                        error_text = "Invalid data type for module_stdin; must be string or byte array"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    client_username = message.get("client_username")
                    if not client_username:
                        error_text = "No client_username for module_stdin specified"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    client = await db.execute(
                        select(Client).where(
                            Client.username == client_username,
                            Client.user_uuid == user.uuid
                        )
                    )
                    client = client.scalar_one_or_none()
                    if not client:
                        error_text = (
                            "No client exists with specified username for module_stdin"
                        )
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    if not client.alive:
                        error_text = "Client is not running"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    payload = {
                        "type": "module_stdin",
                        "from": user.username,
                        "stdin": {
                            "module_name": module_name,
                            "data": data_bytes,
                        },
                    }
                    await client_websocket_manager.send_to_client(
                        str(client.uuid), payload
                    )
                    await websocket.send_text(json.dumps({"type": "ok"}))

                else:
                    logger.debug(
                        "Unhandled user websocket message type: %s",
                        message.get("type"),
                    )

        except WebSocketDisconnect:
            logger.info("User websocket disconnected: %s", user_uuid)
        finally:
            await user_websocket_manager.disconnect(websocket, user_uuid)

    except HTTPException as e:
        logger.warning(
            "User websocket authentication failed: %s", getattr(e, "detail", e)
        )
        await websocket.close(code=e.status_code, reason=e.detail)
    except Exception:
        logger.exception("Unhandled error in user websocket endpoint")
        await websocket.close(code=500, reason="Internal server error")


@router.post("/ws-user-token", response_model=TokenResponse)
async def websocket_user_token(user: User = Depends(get_current_user)):
    """
    Generate a WebSocket authentication token for the current user.

    Creates a special access token that can be used for WebSocket connections.
    This token is separate from the regular HTTP authentication token.

    Args:
        user: Current authenticated user dependency

    Returns:
        TokenResponse: WebSocket access token and token type

    Raises:
        HTTPException: 401 if user is not authenticated
    """
    logger.debug("Issuing user websocket token for '%s'", user.username)
    access_token = create_access_token(user.uuid, TokenType.WEBSOCKET)
    return {"access_token": access_token, "token_type": "websocket"}


@router.websocket("/ws-client")
async def websocket_client(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for client connections.

    Handles WebSocket connections from clients, manages their alive status,
    and processes module output and event messages from clients.

    Args:
        websocket: WebSocket connection instance
        token: Authentication token for client verification
        db: Database session dependency

    Raises:
        WebSocketException: 404 if client not found
        WebSocketException: 401 if token is invalid
        WebSocketException: 500 for server errors
    """
    try:
        client_uuid = verify_websocket_access_token(token)
        logger.info("Client websocket connected: %s", client_uuid)
        client = await db.execute(select(Client).where(Client.uuid == client_uuid))
        client = client.scalar_one_or_none()

        if not client:
            logger.warning(
                "Client websocket rejected: client '%s' not found", client_uuid
            )
            await websocket.close(code=404, reason="Client not found")
            return

        await client_websocket_manager.connect(websocket, client_uuid)
        await _update_client_alive_status(db, client, alive=True)
        await client_websocket_manager.broadcast_client_alive_status(
            client.username, alive=True
        )

        try:
            while True:
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=CLIENT_WEBSOCKET_HEARTBEAT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.debug(
                        "Heartbeat timeout waiting for activity; sending ping to %s",
                        client_uuid,
                    )
                    try:
                        await websocket.send_text(json.dumps({"type": "ping"}))
                    except Exception:
                        logger.warning(
                            "Failed to send heartbeat ping to client %s",
                            client_uuid,
                        )
                        await _update_client_alive_status(db, client, alive=False)
                        await websocket.close(code=1011, reason="Heartbeat timeout")
                        break

                    try:
                        data = await asyncio.wait_for(
                            websocket.receive_text(),
                            timeout=CLIENT_WEBSOCKET_PONG_TIMEOUT_SECONDS,
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Client websocket timeout waiting for pong: %s",
                            client_uuid,
                        )
                        await _update_client_alive_status(db, client, alive=False)
                        await websocket.close(code=1011, reason="Heartbeat timeout")
                        break
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue

                # Expect new message schema from clients
                msg_type = message.get("type")
                if msg_type == "pong":
                    logger.debug("Received pong from client %s", client_uuid)
                    continue
                if msg_type == "console_output":
                    logger.debug(
                        "Module output from client '%s' for module '%s'",
                        client.username,
                        (message.get("output") or {}).get("module_name"),
                    )
                    output = message.get("output")
                    if not output:
                        error_text = "output json not specified for console_output"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    module_name = output.get("module_name")
                    stream = output.get("stream")
                    line = output.get("line")

                    if not module_name:
                        error_text = "module_name not specified for console_output"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    if not stream:
                        error_text = "stream not specified for console_output"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    if not line:
                        error_text = "line not specified for console_output"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    payload = {
                        "type": "console_output",
                        "from": client.username,
                        "output": {
                            "module_name": module_name,
                            "stream": stream,
                            "line": line,
                        },
                    }
                    await user_websocket_manager.broadcast_to_all(payload)
                elif msg_type in {"module_started", "module_exit", "module_canceled"}:
                    event = message.get("event")
                    if event is None:
                        error_text = f"event not specified for {msg_type}"
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue
                    module_name = event.get("module_name")
                    code_val = event.get("code")
                    code = code_val if code_val is not None else ""

                    if not module_name:
                        error_text = "module_name not specified for " + msg_type
                        logger.error(error_text)
                        await websocket.send_text(
                            json.dumps({"type": "error", "message": error_text})
                        )
                        continue

                    logger.debug(
                        "Module event '%s' from client '%s' for module '%s'",
                        msg_type,
                        client.username,
                        module_name,
                    )

                    payload = {
                        "type": msg_type,
                        "from": client.username,
                        "event": {"module_name": module_name, "code": code},
                    }
                    await user_websocket_manager.broadcast_to_all(payload)
                else:
                    logger.debug(
                        "Unhandled client websocket message type: %s", msg_type
                    )

        except WebSocketDisconnect:
            logger.info("Client websocket disconnected: %s", client_uuid)
        finally:
            await client_websocket_manager.disconnect(websocket, client_uuid)
            if client:
                if client.alive:
                    await _update_client_alive_status(db, client, alive=False)
                await client_websocket_manager.broadcast_client_alive_status(
                    client.username, alive=False
                )

    except HTTPException as e:
        logger.warning(
            "Client websocket authentication failed: %s", getattr(e, "detail", e)
        )
        await websocket.close(code=e.status_code, reason=e.detail)
    except Exception:
        logger.exception("Unhandled error in client websocket endpoint")
        await websocket.close(code=500, reason="Internal server error")


@router.post("/ws-client-token")
async def websocket_client_token(client: Client = Depends(get_current_client)):
    """
    Generate a WebSocket authentication token for the current client.

    Creates a special access token that can be used for client WebSocket connections.
    This allows clients to authenticate with the WebSocket endpoint.

    Args:
        client: Current authenticated client dependency

    Returns:
        dict: WebSocket access token and token type

    Raises:
        HTTPException: 401 if client is not authenticated
    """
    logger.debug("Issuing client websocket token for '%s'", client.username)
    access_token = create_access_token(client.uuid, TokenType.WEBSOCKET)
    return {"access_token": access_token, "token_type": "websocket"}

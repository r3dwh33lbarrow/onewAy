import json

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
from app.models.client import Client
from app.models.user import User
from app.schemas.general import TokenResponse
from app.services.authentication import (
    create_access_token,
    get_current_client,
    get_current_user,
    verify_websocket_access_token, TokenType,
)
from app.services.client_websockets import client_websocket_manager
from app.services.user_websockets import user_websocket_manager

router = APIRouter()


@router.websocket("/ws-user")
async def websocket_user_endpoint(
    websocket: WebSocket, token: str = Query(..., description="Authentication token")
):
    """
    WebSocket endpoint for user connections.

    Handles WebSocket connections from users, managing connection lifecycle
    and responding to ping messages to maintain connection health.

    Args:
        websocket: WebSocket connection instance
        token: Authentication token for user verification

    Raises:
        WebSocketException: 401 if token is invalid
        WebSocketException: 500 for server errors
    """
    try:
        user_uuid = verify_websocket_access_token(token)
        await user_websocket_manager.connect(websocket, user_uuid)

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

        except WebSocketDisconnect:
            pass
        finally:
            await user_websocket_manager.disconnect(websocket, user_uuid)

    except HTTPException as e:
        await websocket.close(code=e.status_code, reason=e.detail)
    except Exception:
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
        client = await db.execute(select(Client).where(Client.uuid == client_uuid))
        client = client.scalar_one_or_none()

        if not client:
            await websocket.close(code=404, reason="Client not found")
            return

        await client_websocket_manager.connect(websocket, client_uuid)
        await client_websocket_manager.broadcast_client_alive_status(
            client.username, alive=True
        )

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue

                msg_type = message.get("message_type")
                if msg_type == "module_output":
                    payload = {
                        "type": "console_output",
                        "data": {
                            "username": client.username,
                            "module_name": message.get("module_name"),
                            "stream": message.get("stream"),
                            "line": message.get("line"),
                        },
                    }
                    await user_websocket_manager.broadcast_to_all(payload)
                elif msg_type in {"module_started", "module_exit", "module_canceled"}:
                    payload = {
                        "type": "console_event",
                        "data": {
                            "username": client.username,
                            "module_name": message.get("module_name"),
                            "event": msg_type,
                            "code": message.get("code"),
                        },
                    }
                    await user_websocket_manager.broadcast_to_all(payload)

        except WebSocketDisconnect:
            pass
        finally:
            await client_websocket_manager.disconnect(websocket, client_uuid)
            # Only broadcast alive status if client exists
            if client:
                await client_websocket_manager.broadcast_client_alive_status(
                    client.username, alive=False
                )

    except HTTPException as e:
        await websocket.close(code=e.status_code, reason=e.detail)
    except Exception:
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
    access_token = create_access_token(client.uuid, TokenType.WEBSOCKET)
    return {"access_token": access_token, "token_type": "websocket"}

import json

from fastapi import APIRouter, WebSocket, Query, WebSocketDisconnect, HTTPException, Depends

from app.models.client import Client
from app.models.user import User
from app.schemas.general import TokenResponse
from app.services.authentication import verify_websocket_access_token, get_current_user, create_access_token, \
    get_current_client
from app.services.client_websockets import client_websocket_manager
from app.services.user_websockets import user_websocket_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(..., description="Authentication token")):
    """
    WebSocket endpoint for real-time client status updates.

    Args:
        websocket: The WebSocket connection
        token: Access token passed as query parameter
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


@router.post("/ws-token", response_model=TokenResponse)
async def websocket_token(user: User = Depends(get_current_user)):
    access_token = create_access_token(user.uuid, is_ws=True)
    return {"access_token": access_token, "token_type": "websocket"}


@router.websocket("/ws-client")
async def websocket_client(websocket: WebSocket, token: str = Query(..., description="Authentication token")):
    try:
        client_uuid = verify_websocket_access_token(token)
        await client_websocket_manager(websocket, client_uuid)

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

        except WebSocketDisconnect:
            pass
        finally:
            await client_websocket_manager.disconnect(websocket, client_uuid)

    except HTTPException as e:
        await websocket.close(code=e.status_code, reason=e.detail)
    except Exception:
        await websocket.close(code=500, reason="Internal server error")


@router.post("/ws-client-token")
async def websocket_client_token(client: Client = Depends(get_current_client)):
    access_token = create_access_token(client.uuid, is_ws=True)
    return {"access_token": access_token, "token_type": "websocket"}

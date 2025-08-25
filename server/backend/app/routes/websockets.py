import json

from fastapi import APIRouter, WebSocket, Query, WebSocketDisconnect, HTTPException

from app.services.authentication import verify_websocket_access_token
from app.services.websockets import websocket_manager

router = APIRouter(prefix="/ws")


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
        await websocket_manager.connect(websocket, user_uuid)

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

        except WebSocketDisconnect:
            pass
        finally:
            await websocket_manager.disconnect(websocket)

    except HTTPException as e:
        await websocket.close(code=e.status_code, reason=e.detail)
    except Exception:
        await websocket.close(code=500, reason="Internal server error")

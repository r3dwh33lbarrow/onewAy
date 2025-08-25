import json
import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.authentication import hash_password, create_access_token


@pytest.mark.asyncio
async def test_websocket_connection_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful WebSocket connection with valid token"""
    # Create a user for authentication
    test_user = User(
        username="wsuser",
        hashed_password=hash_password("password123")
    )
    db_session.add(test_user)
    await db_session.commit()

    # Create access token
    access_token = create_access_token(test_user.uuid, is_user=True)

    # Connect to WebSocket with valid token
    async with aconnect_ws(f"ws://testserver/ws?token={access_token}", client) as websocket:
        # Send ping message
        ping_message = {"type": "ping"}
        await websocket.send_text(json.dumps(ping_message))

        # Receive pong response
        response = await websocket.receive_text()
        response_data = json.loads(response)

        assert response_data["type"] == "pong"

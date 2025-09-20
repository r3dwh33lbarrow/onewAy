import json
import pytest
from httpx_ws import aconnect_ws
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.client import Client
from app.services.authentication import create_access_token, TokenType
from app.services.password import hash_password


@pytest.mark.asyncio
async def test_user_websocket_connect(ws_client, db_session: AsyncSession):
    user = User(username="wsadmin", hashed_password=hash_password("pw"))
    db_session.add(user)
    await db_session.commit()

    access_token = create_access_token(user.uuid, TokenType.WEBSOCKET)

    async with ws_client as client:
        async with aconnect_ws(f"/ws-user?token={access_token}", client) as websocket:
            ping_message = {"type": "ping"}
            await websocket.send_text(json.dumps(ping_message))

            response = await websocket.receive_text()
            response_data = json.loads(response)

            assert response_data["type"] == "pong"


@pytest.mark.asyncio
async def test_client_websocket_connect(ws_client, db_session: AsyncSession):
    client_obj = Client(
        username="wsrunner",
        hashed_password=hash_password("pw"),
        ip_address="127.0.0.1",
        client_version="1.0.0"
    )
    db_session.add(client_obj)
    await db_session.commit()

    access_token = create_access_token(client_obj.uuid, TokenType.WEBSOCKET)

    async with ws_client as client:
        async with aconnect_ws(f"/ws-client?token={access_token}", client) as websocket:
            ping_message = {"type": "ping"}
            await websocket.send_text(json.dumps(ping_message))

            response = await websocket.receive_text()
            response_data = json.loads(response)

            assert response_data["type"] == "pong"
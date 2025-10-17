import json

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.user import User
from app.services.authentication import TokenType, create_access_token
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
async def test_ws_user_token(client: AsyncClient):
    await client.post(
        "/user/auth/register", json={"username": "wsuser", "password": "pw"}
    )
    r = await client.post(
        "/user/auth/login", json={"username": "wsuser", "password": "pw"}
    )
    assert r.status_code == 200
    r = await client.post("/ws-user-token")
    assert r.status_code == 200
    data = r.json()
    assert data.get("token_type") == "websocket"
    assert (
        isinstance(data.get("access_token"), str) and len(data.get("access_token")) > 0
    )


@pytest.mark.asyncio
async def test_client_websocket_connect(ws_client, db_session: AsyncSession):
    client_obj = Client(
        username="wsrunner",
        hashed_password=hash_password("pw"),
        ip_address="127.0.0.1",
        client_version="1.0.0",
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


@pytest.mark.asyncio
async def test_ws_client_token(client: AsyncClient):
    await client.post(
        "/client/auth/enroll",
        json={"username": "wsclient", "password": "pw", "client_version": "1.0.0"},
    )
    r = await client.post(
        "/client/auth/login", json={"username": "wsclient", "password": "pw"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "user-agent": "oneway-client"}
    r = await client.post("/ws-client-token", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("token_type") == "websocket"
    assert (
        isinstance(data.get("access_token"), str) and len(data.get("access_token")) > 0
    )

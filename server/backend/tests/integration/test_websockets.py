import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from httpx_ws import aconnect_ws
from app.main import app
from app.dependencies import get_db, init_db, cleanup_db
from tests.conftest import TestAsyncSessionLocal


@pytest_asyncio.fixture(scope="function")
async def ws_client_with_override() -> AsyncClient:
    async def _override_get_db():
        async with TestAsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    await cleanup_db()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_websocket_user_token_success(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    response = await client.post("/ws-user-token")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "websocket"


@pytest.mark.asyncio
async def test_websocket_user_endpoint_success(client: AsyncClient, ws_client_with_override: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    token_response = await client.post("/ws-user-token")
    token = token_response.json()["access_token"]

    async with aconnect_ws(f"/ws-user?token={token}", ws_client_with_override) as ws:
        await ws.send_json({"type": "ping"})
        response = await ws.receive_json()
        assert response == {"type": "pong"}


@pytest.mark.asyncio
async def test_websocket_client_token_success(client: AsyncClient):
    await client.post(
        "/client/auth/enroll",
        json={
            "username": "testclient",
            "password": "testpassword",
            "client_version": "1.0.0",
        },
    )
    login_response = await client.post(
        "/client/auth/login",
        json={"username": "testclient", "password": "testpassword"},
    )
    access_token = login_response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {access_token}"
    client.headers["user-agent"] = "oneway-test-client"
    response = await client.post("/ws-client-token")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "websocket"


@pytest.mark.asyncio
async def test_websocket_client_endpoint_success(client: AsyncClient, ws_client_with_override: AsyncClient):
    await client.post(
        "/client/auth/enroll",
        json={
            "username": "testclient",
            "password": "testpassword",
            "client_version": "1.0.0",
        },
    )
    login_response = await client.post(
        "/client/auth/login",
        json={"username": "testclient", "password": "testpassword"},
    )
    access_token = login_response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {access_token}"
    client.headers["user-agent"] = "oneway-test-client"
    token_response = await client.post("/ws-client-token")
    token = token_response.json()["access_token"]

    async with aconnect_ws(f"/ws-client?token={token}", ws_client_with_override) as ws:
        await ws.send_json({"type": "ping"})
        response = await ws.receive_json()
        assert response == {"type": "pong"}
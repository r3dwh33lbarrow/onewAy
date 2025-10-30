import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def register_user(client: AsyncClient, username: str, password: str = "pw"):
    response = await client.post(
        "/user/auth/register", json={"username": username, "password": password}
    )
    assert response.status_code == 200
    assert response.json() == {"result": "success"}


async def login_user(client: AsyncClient, username: str, password: str = "pw"):
    response = await client.post(
        "/user/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200
    assert response.json() == {"result": "success"}
    assert client.cookies.get("access_token")
    return response


@pytest.mark.parametrize("username", ["alice", "bob"])
async def test_register_login_logout_flow(client: AsyncClient, username: str):
    await register_user(client, username)
    await login_user(client, username)
    assert client.cookies.get("access_token") is not None

    logout_response = await client.post("/user/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {"result": "success"}
    assert client.cookies.get("access_token") is None


async def test_register_rejects_duplicate_usernames(client: AsyncClient):
    await register_user(client, "duplicate")
    conflict = await client.post(
        "/user/auth/register", json={"username": "duplicate", "password": "pw"}
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "Username already exists"


async def test_login_rejects_invalid_credentials(client: AsyncClient):
    await register_user(client, "invalid_user")
    bad_password = await client.post(
        "/user/auth/login", json={"username": "invalid_user", "password": "wrong"}
    )
    assert bad_password.status_code == 401

    missing_user = await client.post(
        "/user/auth/login", json={"username": "ghost", "password": "pw"}
    )
    assert missing_user.status_code == 401


async def test_logout_without_prior_login_succeeds(client: AsyncClient):
    response = await client.post("/user/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"result": "success"}


async def test_ws_token_requires_authentication(client: AsyncClient):
    unauthorized = await client.post("/user/auth/ws-token")
    assert unauthorized.status_code == 401

    await register_user(client, "wsuser")
    await login_user(client, "wsuser")
    token_response = await client.post("/user/auth/ws-token")
    assert token_response.status_code == 200
    payload = token_response.json()
    assert payload["token_type"] == "websocket"
    assert isinstance(payload["access_token"], str) and payload["access_token"]


async def test_login_updates_last_login_timestamp(client: AsyncClient):
    await register_user(client, "timestamp_user")
    await login_user(client, "timestamp_user")
    response = await client.get("/user/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "timestamp_user"
    assert payload["last_login"] is not None

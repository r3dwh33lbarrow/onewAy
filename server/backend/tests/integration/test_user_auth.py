import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_user_success(client: AsyncClient):
    response = await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 200
    assert response.json() == {"result": "success"}


async def test_register_user_duplicate(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    response = await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Username already exists"}


async def test_login_user_success(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    response = await client.post(
        "/user/auth/login",
        json={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 200
    assert response.json() == {"result": "success"}
    assert "access_token" in response.cookies


async def test_login_user_invalid_credentials(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    response = await client.post(
        "/user/auth/login",
        json={"username": "testuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


async def test_logout_user(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login",
        json={"username": "testuser", "password": "testpassword"},
    )
    response = await client.post("/user/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"result": "success"}
    assert response.cookies.get("access_token") is None or response.cookies.get("access_token") == ""


async def test_get_ws_token_success(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login",
        json={"username": "testuser", "password": "testpassword"},
    )
    response = await client.post("/user/auth/ws-token")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "websocket"


async def test_get_ws_token_unauthorized(client: AsyncClient):
    response = await client.post("/user/auth/ws-token")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing access token cookie"}
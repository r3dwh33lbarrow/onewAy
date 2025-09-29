import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_client_enroll_and_login(client: AsyncClient):
    r = await client.post(
        "/client/auth/enroll",
        json={"username": "authuser", "password": "pw123", "client_version": "1.0.0"},
    )
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    r = await client.post(
        "/client/auth/login", json={"username": "authuser", "password": "pw123"}
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_login_with_invalid_credentials(client: AsyncClient):
    await client.post(
        "/client/auth/enroll",
        json={"username": "baduser", "password": "goodpw", "client_version": "1.0.0"},
    )
    r = await client.post(
        "/client/auth/login", json={"username": "baduser", "password": "wrongpw"}
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_enroll_duplicate_username(client: AsyncClient):
    payload = {"username": "dupeuser", "password": "pw", "client_version": "1.0.0"}
    r = await client.post("/client/auth/enroll", json=payload)
    assert r.status_code == 200
    r = await client.post("/client/auth/enroll", json=payload)
    assert r.status_code == 409
    assert r.json()["detail"] == "Username already exists"


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    await client.post(
        "/client/auth/enroll",
        json={"username": "refreshuser", "password": "pw", "client_version": "1.0.0"},
    )
    r = await client.post(
        "/client/auth/login", json={"username": "refreshuser", "password": "pw"}
    )
    assert r.status_code == 200
    refresh_cookie = r.cookies.get("refresh_token")
    assert refresh_cookie

    client.cookies.set("refresh_token", refresh_cookie)
    r = await client.post("/client/auth/refresh")
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"

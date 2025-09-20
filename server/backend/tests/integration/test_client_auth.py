import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def set_user_agent(client: AsyncClient):
    client.headers["user-agent"] = "oneway-test-client"


async def test_enroll_client_success(client: AsyncClient):
    response = await client.post(
        "/client/auth/enroll",
        json={
            "username": "testclient",
            "password": "testpassword",
            "client_version": "1.0.0",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"result": "success"}


async def test_enroll_client_duplicate(client: AsyncClient):
    await client.post(
        "/client/auth/enroll",
        json={
            "username": "testclient",
            "password": "testpassword",
            "client_version": "1.0.0",
        },
    )
    response = await client.post(
        "/client/auth/enroll",
        json={
            "username": "testclient",
            "password": "testpassword",
            "client_version": "1.0.0",
        },
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Username already exists"}


async def test_login_client_success(client: AsyncClient):
    await client.post(
        "/client/auth/enroll",
        json={
            "username": "testclient",
            "password": "testpassword",
            "client_version": "1.0.0",
        },
    )
    response = await client.post(
        "/client/auth/login",
        json={
            "username": "testclient",
            "password": "testpassword",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert "refresh_token" in response.cookies


async def test_login_client_invalid_credentials(client: AsyncClient):
    await client.post(
        "/client/auth/enroll",
        json={
            "username": "testclient",
            "password": "testpassword",
            "client_version": "1.0.0",
        },
    )
    response = await client.post(
        "/client/auth/login",
        json={
            "username": "testclient",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


async def test_refresh_token_success(client: AsyncClient):
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
        json={
            "username": "testclient",
            "password": "testpassword",
        },
    )
    refresh_token = login_response.cookies.get("refresh_token")
    assert refresh_token is not None

    client.cookies.set("refresh_token", refresh_token)

    response = await client.post("/client/auth/refresh")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert "refresh_token" in response.cookies


async def test_refresh_token_invalid(client: AsyncClient):
    client.cookies.set("refresh_token", "invalidtoken")
    response = await client.post("/client/auth/refresh")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}
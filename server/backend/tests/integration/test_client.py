
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_client_me_success(client: AsyncClient):
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
    response = await client.get("/client/me")
    assert response.status_code == 200
    assert response.json() == {"username": "testclient"}


@pytest.mark.asyncio
async def test_client_me_unauthorized(client: AsyncClient):
    client.headers["user-agent"] = "oneway-test-client"
    response = await client.get("/client/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing or invalid authorization header"}


@pytest.mark.asyncio
async def test_client_get_username_success(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    await client.post(
        "/client/auth/enroll",
        json={
            "username": "testclient",
            "password": "testpassword",
            "client_version": "1.0.0",
        },
    )
    response = await client.get("/client/get/testclient")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testclient"


@pytest.mark.asyncio
async def test_client_get_username_not_found(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    response = await client.get("/client/get/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "Client not found"}


@pytest.mark.asyncio
async def test_client_get_username_unauthorized(client: AsyncClient):
    response = await client.get("/client/get/testclient")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing access token cookie"}


@pytest.mark.asyncio
async def test_client_all_success(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    await client.post(
        "/client/auth/enroll",
        json={
            "username": "testclient",
            "password": "testpassword",
            "client_version": "1.0.0",
        },
    )
    response = await client.get("/client/all")
    assert response.status_code == 200
    data = response.json()
    assert "clients" in data
    assert len(data["clients"]) >= 1
    assert data["clients"][0]["username"] == "testclient"


@pytest.mark.asyncio
async def test_client_all_unauthorized(client: AsyncClient):
    response = await client.get("/client/all")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing access token cookie"}


@pytest.mark.asyncio
async def test_client_update_info_success(client: AsyncClient):
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
    response = await client.post(
        "/client/update-info", json={"hostname": "new-hostname"}
    )
    assert response.status_code == 200
    assert response.json() == {"result": "success"}


@pytest.mark.asyncio
async def test_client_update_info_unauthorized(client: AsyncClient):
    client.headers["user-agent"] = "oneway-test-client"
    response = await client.post("/client/update-info", json={"hostname": "new-hostname"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing or invalid authorization header"}

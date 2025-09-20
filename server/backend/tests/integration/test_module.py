import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_module_all_success(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    await client.put(
        "/module/add", json={"module_path": "tests/modules/test_module"}
    )
    response = await client.get("/module/all")
    assert response.status_code == 200
    data = response.json()
    assert "modules" in data
    assert len(data["modules"]) >= 1
    assert data["modules"][0]["name"] == "test_module"


@pytest.mark.asyncio
async def test_module_get_success(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    await client.put(
        "/module/add", json={"module_path": "tests/modules/test_module"}
    )
    response = await client.get("/module/get/test_module")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_module"


@pytest.mark.asyncio
async def test_module_get_not_found(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    response = await client.get("/module/get/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "Module not found"}


@pytest.mark.asyncio
async def test_set_and_get_installed_module(client: AsyncClient):
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
    await client.put(
        "/module/add", json={"module_path": "tests/modules/test_module"}
    )
    response = await client.post(
        "/module/set-installed/testclient", params={"module_name": "test_module"}
    )
    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    response = await client.get("/module/installed/testclient")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test_module"
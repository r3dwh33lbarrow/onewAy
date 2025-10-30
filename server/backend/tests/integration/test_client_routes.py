import os
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.settings import settings

pytestmark = pytest.mark.asyncio


async def register_user(
    client: AsyncClient, username: str = "admin", password: str = "pw"
):
    response = await client.post(
        "/user/auth/register", json={"username": username, "password": password}
    )
    assert response.status_code == 200
    login = await client.post(
        "/user/auth/login", json={"username": username, "password": password}
    )
    assert login.status_code == 200
    assert client.cookies.get("access_token")


async def enroll_client(
    client: AsyncClient,
    username: str,
    password: str = "pw",
    version: str = "0.1.0",
):
    payload = {
        "username": username,
        "password": password,
        "client_version": version,
    }
    response = await client.post("/client/auth/enroll", json=payload)
    assert response.status_code == 200
    return response


async def login_client(
    client: AsyncClient, username: str, password: str = "pw"
) -> tuple[str, dict]:
    response = await client.post(
        "/client/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "user-agent": "oneway-client"}
    return token, headers


async def get_client_me(client: AsyncClient, headers: dict):
    response = await client.get("/client/me", headers=headers)
    assert response.status_code == 200
    return response.json()


async def get_client_details(client: AsyncClient, username: str, headers: dict):
    response = await client.get(f"/client/action/{username}", headers=headers)
    assert response.status_code == 200
    return response.json()


async def get_client_overview(client: AsyncClient, headers: dict):
    response = await client.get("/client/get-all", headers=headers)
    assert response.status_code == 200
    return response.json()


async def update_client_info(client: AsyncClient, headers: dict, payload: dict):
    response = await client.post("/client/update-info", headers=headers, json=payload)
    return response


async def request_update_bundle(client: AsyncClient, headers: dict):
    response = await client.get("/client/update", headers=headers)
    return response


async def delete_client(client: AsyncClient, username: str):
    response = await client.delete(f"/client/action/{username}")
    return response


async def assert_client_deleted(client: AsyncClient, username: str, headers: dict):
    response = await client.get(f"/client/action/{username}", headers=headers)
    assert response.status_code == 404


async def seed_client_environment(
    client: AsyncClient,
    client_username: str,
    client_version: str = "0.1.0",
    admin_username: str = "admin",
    admin_password: str = "pw",
) -> tuple[dict, tuple[str, str]]:
    await register_user(client, admin_username, admin_password)
    await enroll_client(client, client_username, version=client_version)
    _token, headers = await login_client(client, client_username)
    return headers, (admin_username, admin_password)


async def assert_client_list_contains(client: AsyncClient, headers: dict, username: str):
    overview = await get_client_overview(client, headers)
    usernames = {entry["username"] for entry in overview["clients"]}
    assert username in usernames


async def ensure_client_deleted(
    client: AsyncClient,
    username: str,
    headers: dict,
    admin_credentials: tuple[str, str],
):
    admin_username, admin_password = admin_credentials
    await client.post(
        "/user/auth/login",
        json={"username": admin_username, "password": admin_password},
    )
    response = await delete_client(client, username)
    assert response.status_code == 200
    assert response.json() == {"result": "success"}
    await assert_client_deleted(client, username, headers)


@pytest.mark.asyncio
async def test_client_me_returns_authenticated_client(client: AsyncClient):
    headers, _ = await seed_client_environment(client, "me-client", "1.0.0")
    profile = await get_client_me(client, headers)
    assert profile["username"] == "me-client"


@pytest.mark.asyncio
async def test_client_details_and_overview(client: AsyncClient):
    headers, _ = await seed_client_environment(client, "detail-client")
    info = await get_client_details(client, "detail-client", headers)
    assert info["username"] == "detail-client"

    await assert_client_list_contains(client, headers, "detail-client")


@pytest.mark.asyncio
async def test_client_update_info(client: AsyncClient):
    headers, _ = await seed_client_environment(client, "update-client")
    payload = {"hostname": "updated-host", "platform": "windows"}
    response = await update_client_info(client, headers, payload)
    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    info = await get_client_details(client, "update-client", headers)
    assert info["hostname"] == "updated-host"
    assert info["platform"] == "windows"


@pytest.mark.asyncio
async def test_client_update_endpoint_handles_latest_version(client: AsyncClient):
    headers, _ = await seed_client_environment(
        client,
        "latest-client",
        client_version=settings.app.client_version,
    )
    response = await request_update_bundle(client, headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "Client already at latest version"


@pytest.mark.asyncio
async def test_client_update_missing_binary_returns_error(client: AsyncClient):
    headers, _ = await seed_client_environment(
        client,
        "bundle-client",
        client_version="0.0.1",
    )
    response = await request_update_bundle(client, headers)
    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to find client binary"


@pytest.mark.asyncio
async def test_client_delete_removes_bucket_entries(client: AsyncClient):
    headers, admin_credentials = await seed_client_environment(
        client, "delete-client"
    )
    await ensure_client_deleted(client, "delete-client", headers, admin_credentials)


@pytest.mark.asyncio
async def test_client_get_unknown_returns_404(client: AsyncClient):
    headers, _ = await seed_client_environment(client, "known-client")
    response = await client.get(
        "/client/action/unknown-client", headers=headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"

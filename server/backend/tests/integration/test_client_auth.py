import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def register_user(client: AsyncClient, username: str = "admin", password: str = "pw"):
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
    version: str = "1.0.0",
):
    payload = {
        "username": username,
        "password": password,
        "client_version": version,
    }
    response = await client.post("/client/auth/enroll", json=payload)
    return response


async def login_client(
    client: AsyncClient, username: str, password: str = "pw"
):
    response = await client.post(
        "/client/auth/login", json={"username": username, "password": password}
    )
    return response


async def refresh_client_token(client: AsyncClient):
    response = await client.post("/client/auth/refresh")
    return response


async def revoke_client_credentials(client: AsyncClient, username: str):
    response = await client.delete(f"/client/{username}/revoke-tokens")
    assert response.status_code == 200
    assert response.json() == {"result": "success"}


@pytest.mark.asyncio
async def test_client_enroll_login_and_refresh_flow(client: AsyncClient):
    await register_user(client)

    enroll = await enroll_client(client, "agent-one")
    assert enroll.status_code == 200
    assert enroll.json() == {"result": "success"}

    login = await login_client(client, "agent-one")
    assert login.status_code == 200
    payload = login.json()
    assert payload["token_type"] == "Bearer"
    assert isinstance(payload["access_token"], str) and payload["access_token"]

    refresh_cookie = login.cookies.get("refresh_token")
    assert refresh_cookie
    client.cookies.set("refresh_token", refresh_cookie)

    refreshed = await refresh_client_token(client)
    assert refreshed.status_code == 200
    refreshed_payload = refreshed.json()
    assert refreshed_payload["token_type"] == "Bearer"
    assert isinstance(refreshed_payload["access_token"], str)


@pytest.mark.asyncio
async def test_client_enroll_requires_unique_username(client: AsyncClient):
    await register_user(client)

    first = await enroll_client(client, "duplicate-client")
    assert first.status_code == 200

    duplicate = await enroll_client(client, "duplicate-client")
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Username already exists"


@pytest.mark.asyncio
async def test_client_login_rejects_bad_credentials(client: AsyncClient):
    await register_user(client)
    await enroll_client(client, "bad-creds", password="goodpw")

    wrong_password = await login_client(client, "bad-creds", password="wrongpw")
    assert wrong_password.status_code == 401
    assert wrong_password.json()["detail"] == "Invalid username or password"

    unknown_client = await login_client(client, "ghost-client")
    assert unknown_client.status_code == 401
    assert unknown_client.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_refresh_requires_valid_cookie(client: AsyncClient):
    await register_user(client)
    await enroll_client(client, "refreshless")
    no_cookie_response = await refresh_client_token(client)
    assert no_cookie_response.status_code == 401


@pytest.mark.asyncio
async def test_revoked_client_cannot_login(client: AsyncClient):
    await register_user(client)
    await enroll_client(client, "revoked-agent")

    login = await login_client(client, "revoked-agent")
    assert login.status_code == 200

    await revoke_client_credentials(client, "revoked-agent")

    relogin = await login_client(client, "revoked-agent")
    assert relogin.status_code == 401
    assert relogin.json()["detail"] == "Invalid username or password"

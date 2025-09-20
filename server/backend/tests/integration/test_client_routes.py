import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_client_me(client: AsyncClient):
    enroll_payload = {
        "username": "testuser",
        "password": "pw123",
        "client_version": "0.1.0"
    }
    r = await client.post("/client/auth/enroll", json=enroll_payload)
    assert r.status_code == 200

    login_payload = {"username": "testuser", "password": "pw123"}
    r = await client.post("/client/auth/login", json=login_payload)
    assert r.status_code == 200
    token = r.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}", "user-agent": "oneway-client"}
    r = await client.get("/client/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_client_get_and_all(client: AsyncClient):
    await client.post("/client/auth/enroll", json={
        "username": "alice",
        "password": "pw",
        "client_version": "0.2.0"
    })
    r = await client.post("/client/auth/login", json={"username": "alice", "password": "pw"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "user-agent": "oneway-client"}

    r = await client.get("/client/get/alice", headers=headers)
    assert r.status_code == 200
    assert r.json()["username"] == "alice"

    r = await client.get("/client/all", headers=headers)
    assert r.status_code == 200
    usernames = [c["username"] for c in r.json()["clients"]]
    assert "alice" in usernames


@pytest.mark.asyncio
async def test_client_update_info(client: AsyncClient):
    await client.post("/client/auth/enroll", json={
        "username": "bob",
        "password": "pw",
        "client_version": "0.5.0"
    })
    r = await client.post("/client/auth/login", json={"username": "bob", "password": "pw"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "user-agent": "oneway-client"}

    payload = {"hostname": "bob-new", "last_known_location": "UK"}
    r = await client.post("/client/update-info", headers=headers, json=payload)
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    r = await client.get("/client/get/bob", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["hostname"] == "bob-new"
    assert data["last_known_location"] == "UK"


@pytest.mark.asyncio
async def test_client_update_already_latest(client: AsyncClient):
    # Enroll client at exactly the current server version
    from app.settings import settings

    await client.post(
        "/client/auth/enroll",
        json={
            "username": "latestguy",
            "password": "pw",
            "client_version": settings.app.client_version,
        },
    )
    r = await client.post(
        "/client/auth/login",
        json={"username": "latestguy", "password": "pw"},
    )
    token = r.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "user-agent": "oneway-client",
    }

    r = await client.get("/client/update", headers=headers)
    assert r.status_code == 400
    assert r.json()["detail"] == "Client already at latest version"


@pytest.mark.asyncio
async def test_client_update_missing_binary(client: AsyncClient):
    # Enroll client with an older version to trigger binary download path
    await client.post(
        "/client/auth/enroll",
        json={
            "username": "needsupdate",
            "password": "pw",
            "client_version": "0.0.1",
        },
    )
    r = await client.post(
        "/client/auth/login",
        json={"username": "needsupdate", "password": "pw"},
    )
    token = r.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "user-agent": "oneway-client",
    }

    r = await client.get("/client/update", headers=headers)
    # In tests there is no client binary in the target path
    assert r.status_code == 500
    assert r.json()["detail"] == "Unable to find client binary"


@pytest.mark.asyncio
async def test_client_get_unknown_returns_404(client: AsyncClient):
    # Prepare an authenticated client
    await client.post(
        "/client/auth/enroll",
        json={
            "username": "lookupper",
            "password": "pw",
            "client_version": "1.0.0",
        },
    )
    r = await client.post(
        "/client/auth/login",
        json={"username": "lookupper", "password": "pw"},
    )
    token = r.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "user-agent": "oneway-client",
    }

    r = await client.get("/client/get/no_such_user", headers=headers)
    assert r.status_code == 404
    assert r.json()["detail"] == "Client not found"

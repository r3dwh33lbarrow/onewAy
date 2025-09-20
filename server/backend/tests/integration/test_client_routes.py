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

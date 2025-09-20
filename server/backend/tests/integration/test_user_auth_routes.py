import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_register_and_login(client: AsyncClient):
    r = await client.post("/user/auth/register", json={"username": "alice", "password": "pw"})
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    r = await client.post("/user/auth/login", json={"username": "alice", "password": "pw"})
    assert r.status_code == 200
    assert r.json() == {"result": "success"}
    assert "access_token" in r.cookies


@pytest.mark.asyncio
async def test_user_login_wrong_password(client: AsyncClient):
    await client.post("/user/auth/register", json={"username": "bob", "password": "pw"})
    r = await client.post("/user/auth/login", json={"username": "bob", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_user_login_nonexistent_user(client: AsyncClient):
    r = await client.post("/user/auth/login", json={"username": "ghost", "password": "pw"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookie(client: AsyncClient):
    await client.post("/user/auth/register", json={"username": "dave", "password": "pw"})
    r = await client.post("/user/auth/login", json={"username": "dave", "password": "pw"})
    assert "access_token" in r.cookies

    r = await client.post("/user/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"result": "success"}
    assert "access_token" not in r.cookies

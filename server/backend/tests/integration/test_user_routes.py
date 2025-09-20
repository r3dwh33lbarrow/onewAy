import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, username="tester", password="pw"):
    await client.post("/user/auth/register", json={"username": username, "password": password})
    r = await client.post("/user/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    client.cookies.set("access_token", r.cookies.get("access_token"))
    return username, password


@pytest.mark.asyncio
async def test_user_me(client: AsyncClient):
    username, _ = await _register_and_login(client, "meuser")
    r = await client.get("/user/me")
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == username
    assert isinstance(data["is_admin"], bool)
    assert "last_login" in data
    assert "created_at" in data
    assert isinstance(data["avatar_set"], bool)


@pytest.mark.asyncio
async def test_user_patch_username_success(client: AsyncClient):
    _, password = await _register_and_login(client, "oldname")
    r = await client.patch("/user", json={"username": "newname"})
    assert r.status_code == 200
    assert r.json() == {"result": "success"}
    await client.post("/user/auth/logout")
    r = await client.post("/user/auth/login", json={"username": "newname", "password": password})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_user_patch_username_empty_and_conflict(client: AsyncClient):
    await _register_and_login(client, "alice")
    r = await client.patch("/user", json={"username": ""})
    assert r.status_code == 422
    await client.post("/user/auth/register", json={"username": "bob", "password": "pw"})
    r = await client.patch("/user", json={"username": "bob"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_user_avatar_flow(client: AsyncClient, tmp_path):
    await _register_and_login(client, "avataruser")
    r = await client.put(
        "/user/avatar",
        files={"file": ("avatar.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 400
    r = await client.put(
        "/user/avatar",
        files={"file": ("avatar.png", b"", "image/png")},
    )
    assert r.status_code == 400
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
        b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDAT"
        b"x\xdac`\x00\x00\x00\x02\x00\x01\xe2!\xbc3"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = await client.put(
        "/user/avatar",
        files={"file": ("avatar.png", png_bytes, "image/png")},
    )
    assert r.status_code == 200
    assert r.json() == {"result": "success"}
    r = await client.get("/user/avatar")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content.startswith(b"\x89PNG")

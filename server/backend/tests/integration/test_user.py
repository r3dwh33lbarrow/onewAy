import pytest
from httpx import AsyncClient
from app.settings import settings
import os


@pytest.mark.asyncio
async def test_user_get_me_success(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    response = await client.get("/user/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_user_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/user/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing access token cookie"}


@pytest.mark.asyncio
async def test_user_patch_username_success(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    response = await client.patch(
        "/user", json={"username": "newtestuser"}
    )
    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    me_response = await client.get("/user/me")
    assert me_response.json()["username"] == "newtestuser"


@pytest.mark.asyncio
async def test_user_patch_username_duplicate(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    # Create another user
    async with AsyncClient(transport=client._transport, base_url=client.base_url) as new_client:
        await new_client.post(
            "/user/auth/register",
            json={"username": "anotheruser", "password": "testpassword"},
        )

    response = await client.patch(
        "/user", json={"username": "anotheruser"}
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Username already exists"}


@pytest.mark.asyncio
async def test_user_patch_username_empty(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    response = await client.patch("/user", json={"username": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_user_get_default_avatar(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    avatar_dir = settings.paths.avatar_dir
    if not os.path.exists(avatar_dir):
        os.makedirs(avatar_dir)
    with open(os.path.join(avatar_dir, "default_avatar.png"), "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    response = await client.get("/user/avatar")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_user_put_avatar_success(client: AsyncClient):
    await client.post(
        "/user/auth/register",
        json={"username": "testuser", "password": "testpassword"},
    )
    await client.post(
        "/user/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    avatar_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    files = {"file": ("avatar.png", avatar_content, "image/png")}
    response = await client.put("/user/avatar", files=files)
    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    me_response = await client.get("/user/me")
    assert me_response.json()["avatar_set"] is True

    avatar_response = await client.get("/user/avatar")
    assert avatar_response.status_code == 200
    assert avatar_response.content == avatar_content

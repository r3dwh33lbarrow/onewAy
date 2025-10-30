import pytest
from httpx import AsyncClient

from app.settings import settings

pytestmark = pytest.mark.asyncio

VALID_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\x0f\x00\x01"
    b"\x01\x01\x00\x18\xdd\x8f\xb3\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def register_and_login(
    client: AsyncClient, username: str, password: str = "pw"
) -> tuple[str, str]:
    register_response = await client.post(
        "/user/auth/register", json={"username": username, "password": password}
    )
    assert register_response.status_code == 200

    login_response = await client.post(
        "/user/auth/login", json={"username": username, "password": password}
    )
    assert login_response.status_code == 200
    assert client.cookies.get("access_token")
    return username, password


async def get_profile(client: AsyncClient) -> dict:
    response = await client.get("/user/me")
    assert response.status_code == 200
    return response.json()


async def upload_avatar(
    client: AsyncClient, filename: str, payload: bytes, content_type: str
):
    return await client.put(
        "/user/avatar", files={"file": (filename, payload, content_type)}
    )


async def fetch_avatar(client: AsyncClient):
    response = await client.get("/user/avatar")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    return response.content


async def relogin(client: AsyncClient, username: str, password: str):
    await client.post("/user/auth/logout")
    response = await client.post(
        "/user/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200


async def login_should_fail(client: AsyncClient, username: str, password: str):
    response = await client.post(
        "/user/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 401


async def ensure_default_avatar(client: AsyncClient):
    await register_and_login(client, "default_avatar_user")
    content = await fetch_avatar(client)
    assert content.startswith(b"\x89PNG")


async def ensure_conflicting_username(client: AsyncClient, username: str):
    response = await client.post(
        "/user/auth/register", json={"username": username, "password": "pw"}
    )
    assert response.status_code == 200


async def ensure_avatar_size_limit(client: AsyncClient):
    await register_and_login(client, "limit_user")
    oversized = b"\x89PNG" + b"\x00" * (
        settings.other.max_avatar_size_mb * 1024 * 1024 + 1
    )
    response = await upload_avatar(client, "avatar.png", oversized, "image/png")
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]


async def ensure_avatar_validation_errors(client: AsyncClient):
    await register_and_login(client, "validation_user")

    wrong_type = await upload_avatar(client, "avatar.txt", b"text", "text/plain")
    assert wrong_type.status_code == 400
    assert wrong_type.json()["detail"] == "Avatar must be a PNG file"

    empty_file = await upload_avatar(client, "avatar.png", b"", "image/png")
    assert empty_file.status_code == 400
    assert empty_file.json()["detail"] == "Empty file"

    wrong_magic = await upload_avatar(client, "avatar.png", b"GIF89a", "image/png")
    assert wrong_magic.status_code == 400
    assert wrong_magic.json()["detail"] == "Avatar must be a PNG file"


async def upload_valid_avatar(client: AsyncClient):
    response = await upload_avatar(client, "avatar.png", VALID_PNG, "image/png")
    assert response.status_code == 200
    assert response.json() == {"result": "success"}
    content = await fetch_avatar(client)
    assert content.startswith(b"\x89PNG")


async def ensure_profile_fields(payload: dict, username: str):
    assert payload["username"] == username
    assert isinstance(payload["is_admin"], bool)
    assert payload["created_at"] is not None
    assert payload["last_login"] is not None


async def ensure_avatar_flag(profile: dict, expected: bool):
    assert profile["avatar_set"] is expected


async def ensure_username_conflict(client: AsyncClient, username: str):
    response = await client.patch("/user", json={"username": username})
    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"


async def ensure_empty_username_rejected(client: AsyncClient):
    response = await client.patch("/user", json={"username": ""})
    assert response.status_code == 422


async def ensure_username_update(client: AsyncClient, new_username: str):
    response = await client.patch("/user", json={"username": new_username})
    assert response.status_code == 200
    assert response.json() == {"result": "success"}


@pytest.mark.asyncio
async def test_get_me_returns_current_user(client: AsyncClient):
    username, _ = await register_and_login(client, "profile_user")
    profile = await get_profile(client)
    await ensure_profile_fields(profile, username)
    await ensure_avatar_flag(profile, False)


@pytest.mark.asyncio
async def test_patch_username_success(client: AsyncClient):
    original, password = await register_and_login(client, "rename_me")
    await ensure_username_update(client, "renamed_user")

    await relogin(client, "renamed_user", password)
    profile = await get_profile(client)
    await ensure_profile_fields(profile, "renamed_user")

    await login_should_fail(client, original, password)


@pytest.mark.asyncio
async def test_patch_username_validation_and_conflict(client: AsyncClient):
    await register_and_login(client, "validation_owner")
    await ensure_empty_username_rejected(client)

    await ensure_conflicting_username(client, "taken_name")
    await ensure_username_conflict(client, "taken_name")


@pytest.mark.asyncio
async def test_avatar_upload_validation_and_success(client: AsyncClient):
    await ensure_avatar_validation_errors(client)
    await upload_valid_avatar(client)


@pytest.mark.asyncio
async def test_avatar_upload_success_sets_flag(client: AsyncClient):
    username, _ = await register_and_login(client, "avatar_success")
    await upload_valid_avatar(client)
    profile = await get_profile(client)
    await ensure_profile_fields(profile, username)
    await ensure_avatar_flag(profile, True)


@pytest.mark.asyncio
async def test_avatar_size_limit(client: AsyncClient):
    await ensure_avatar_size_limit(client)


@pytest.mark.asyncio
async def test_default_avatar_served_when_none_uploaded(client: AsyncClient):
    await ensure_default_avatar(client)

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.password import hash_password

pytestmark = pytest.mark.asyncio


async def create_test_user(db: AsyncSession, username: str, password: str = "pw"):
    """Helper to create a test user directly in the database."""
    hashed_password = hash_password(password)
    user = User(username=username, hashed_password=hashed_password, is_admin=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login_user(client: AsyncClient, username: str, password: str = "pw"):
    response = await client.post(
        "/user/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200
    assert response.json() == {"result": "success"}
    assert client.cookies.get("access_token")
    return response


@pytest.mark.parametrize("username", ["alice", "bob"])
async def test_login_logout_flow(
    client: AsyncClient, db_session: AsyncSession, username: str
):
    """Test that users can login and logout successfully."""
    await create_test_user(db_session, username)
    await login_user(client, username)
    assert client.cookies.get("access_token") is not None

    logout_response = await client.post("/user/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {"result": "success"}
    assert client.cookies.get("access_token") is None


async def test_login_rejects_invalid_credentials(
    client: AsyncClient, db_session: AsyncSession
):
    """Test that login fails with incorrect password."""
    await create_test_user(db_session, "invalid_user", "correct_password")

    bad_password = await client.post(
        "/user/auth/login", json={"username": "invalid_user", "password": "wrong"}
    )
    assert bad_password.status_code == 401

    missing_user = await client.post(
        "/user/auth/login", json={"username": "ghost", "password": "pw"}
    )
    assert missing_user.status_code == 401


async def test_logout_without_prior_login_succeeds(client: AsyncClient):
    """Test that logout works even when not logged in."""
    response = await client.post("/user/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"result": "success"}


async def test_ws_token_requires_authentication(
    client: AsyncClient, db_session: AsyncSession
):
    """Test that websocket token endpoint requires authentication."""
    unauthorized = await client.post("/user/auth/ws-token")
    assert unauthorized.status_code == 401

    await create_test_user(db_session, "wsuser")
    await login_user(client, "wsuser")
    token_response = await client.post("/user/auth/ws-token")
    assert token_response.status_code == 200
    payload = token_response.json()
    assert payload["token_type"] == "websocket"
    assert isinstance(payload["access_token"], str) and payload["access_token"]


async def test_login_updates_last_login_timestamp(
    client: AsyncClient, db_session: AsyncSession
):
    """Test that login updates the last_login timestamp."""
    await create_test_user(db_session, "timestamp_user")
    await login_user(client, "timestamp_user")
    response = await client.get("/user/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "timestamp_user"
    assert payload["last_login"] is not None


async def test_multiple_login_sessions(client: AsyncClient, db_session: AsyncSession):
    """Test that a user can login multiple times."""
    await create_test_user(db_session, "multi_session_user")

    await login_user(client, "multi_session_user")
    first_token = client.cookies.get("access_token")
    assert first_token is not None

    await client.post("/user/auth/logout")

    await login_user(client, "multi_session_user")
    second_token = client.cookies.get("access_token")
    assert second_token is not None


async def test_login_with_empty_credentials(client: AsyncClient):
    """Test that login rejects empty credentials."""
    empty_username = await client.post(
        "/user/auth/login", json={"username": "", "password": "password"}
    )
    assert empty_username.status_code in [400, 401, 422]

    empty_password = await client.post(
        "/user/auth/login", json={"username": "user", "password": ""}
    )
    assert empty_password.status_code in [400, 401, 422]


async def test_access_protected_route_requires_auth(client: AsyncClient):
    """Test that protected routes require authentication."""
    response = await client.get("/user/me")
    assert response.status_code == 401


async def test_access_protected_route_with_auth(
    client: AsyncClient, db_session: AsyncSession
):
    """Test that protected routes work with valid authentication."""
    await create_test_user(db_session, "protected_user")
    await login_user(client, "protected_user")

    response = await client.get("/user/me")
    assert response.status_code == 200
    assert response.json()["username"] == "protected_user"

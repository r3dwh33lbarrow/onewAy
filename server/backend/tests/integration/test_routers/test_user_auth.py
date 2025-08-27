import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.services.password import hash_password


@pytest.mark.asyncio
async def test_user_register_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful user register"""
    register_data = {
        "username": "testuser",
        "password": "testpassword123"
    }

    response = await client.post("/user/auth/register", json=register_data)

    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    # Verify the user was created in the database
    result = await db_session.execute(select(User).where(User.username == "testuser"))
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.username == "testuser"
    assert created_user.hashed_password != "testpassword123"  # Should be hashed


@pytest.mark.asyncio
async def test_user_register_duplicate_username(client: AsyncClient, db_session: AsyncSession):
    """Test register with an already existing username"""
    # First, create a user
    register_data = {
        "username": "existinguser",
        "password": "password123"
    }

    # First register should succeed
    response = await client.post("/user/auth/register", json=register_data)
    assert response.status_code == 200

    # Second register with same username should fail
    response = await client.post("/user/auth/register", json=register_data)
    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"


@pytest.mark.asyncio
async def test_user_register_missing_username(client: AsyncClient):
    """Test register with missing username"""
    register_data = {
        "password": "testpassword123"
    }

    response = await client.post("/user/auth/register", json=register_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_user_register_missing_password(client: AsyncClient):
    """Test register with missing password"""
    register_data = {
        "username": "testuser"
    }

    response = await client.post("/user/auth/register", json=register_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "register_data",
    [
        {"username": "", "password": "testpassword123"},
        {"username": "testuser", "password": ""},
        {"username": "", "password": ""},
    ],
)
async def test_user_register_empty_fields(client: AsyncClient, register_data):
    """Test register with empty string fields"""
    response = await client.post("/user/auth/register", json=register_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_user_register_invalid_json(client: AsyncClient):
    """Test register with invalid JSON payload"""
    response = await client.post("/user/auth/register", content="invalid json")
    assert response.status_code == 422


# login ENDPOINT TESTS

@pytest.mark.asyncio
async def test_user_login_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful user login"""
    # First create a user
    test_user = User(
        username="loginuser",
        hashed_password=hash_password("password123")
    )
    db_session.add(test_user)
    await db_session.commit()

    login_data = {
        "username": "loginuser",
        "password": "password123"
    }

    response = await client.post("/user/auth/login", json=login_data)

    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    # Verify access token cookie is set
    assert "access_token" in response.cookies

    # Verify last_login was updated
    await db_session.refresh(test_user)
    assert test_user.last_login is not None


@pytest.mark.asyncio
async def test_user_login_invalid_username(client: AsyncClient, db_session: AsyncSession):
    """Test login with non-existent username"""
    login_data = {
        "username": "nonexistentuser",
        "password": "password123"
    }

    response = await client.post("/user/auth/login", json=login_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_user_login_invalid_password(client: AsyncClient, db_session: AsyncSession):
    """Test login with incorrect password"""
    # First create a user
    test_user = User(
        username="loginuser2",
        hashed_password=hash_password("correctpassword")
    )
    db_session.add(test_user)
    await db_session.commit()

    login_data = {
        "username": "loginuser2",
        "password": "wrongpassword"
    }

    response = await client.post("/user/auth/login", json=login_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_user_login_missing_fields(client: AsyncClient):
    """Test login with missing required fields"""
    # Missing password
    login_data = {
        "username": "testuser"
    }

    response = await client.post("/user/auth/login", json=login_data)
    assert response.status_code == 422

    # Missing username
    login_data = {
        "password": "password123"
    }

    response = await client.post("/user/auth/login", json=login_data)
    assert response.status_code == 422

    # Empty payload
    response = await client.post("/user/auth/login", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_user_login_empty_fields(client: AsyncClient):
    """Test login with empty username/password"""
    login_data = {
        "username": "",
        "password": ""
    }

    response = await client.post("/user/auth/login", json=login_data)
    assert response.status_code in [401, 422]  # Could be validation error or auth error

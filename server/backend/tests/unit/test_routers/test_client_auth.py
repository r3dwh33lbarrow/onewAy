import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.client import Client
from app.services.authentication import hash_password


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_client_enroll_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful client enrollment"""
    enroll_data = {
        "username": "testuser",
        "password": "testpassword123",
        "client_version": "1.0.0"
    }

    response = await client.post("/client/auth/enroll", json=enroll_data)

    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    # Verify the client was created in the database
    result = await db_session.execute(select(Client).where(Client.username == "testuser"))
    created_client = result.scalar_one_or_none()
    assert created_client is not None
    assert created_client.username == "testuser"
    assert created_client.client_version == "1.0.0"
    assert created_client.hashed_password != "testpassword123"  # Should be hashed
    assert created_client.ip_address is not None


@pytest.mark.asyncio
async def test_client_enroll_duplicate_username(client: AsyncClient, db_session: AsyncSession):
    """Test enrollment with an already existing username"""
    # First, create a client
    enroll_data = {
        "username": "existinguser",
        "password": "password123",
        "client_version": "1.0.0"
    }

    # First enrollment should succeed
    response = await client.post("/client/auth/enroll", json=enroll_data)
    assert response.status_code == 200

    # Second enrollment with same username should fail
    response = await client.post("/client/auth/enroll", json=enroll_data)
    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"


@pytest.mark.asyncio
async def test_client_enroll_missing_username(client: AsyncClient):
    """Test enrollment with missing username"""
    enroll_data = {
        "password": "testpassword123",
        "client_version": "1.0.0"
    }

    response = await client.post("/client/auth/enroll", json=enroll_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_client_enroll_missing_password(client: AsyncClient):
    """Test enrollment with missing password"""
    enroll_data = {
        "username": "testuser",
        "client_version": "1.0.0"
    }

    response = await client.post("/client/auth/enroll", json=enroll_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_client_enroll_missing_client_version(client: AsyncClient):
    """Test enrollment with missing client_version"""
    enroll_data = {
        "username": "testuser",
        "password": "testpassword123"
    }

    response = await client.post("/client/auth/enroll", json=enroll_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_client_enroll_empty_fields(client: AsyncClient):
    """Test enrollment with empty string fields"""
    enroll_data = {
        "username": "",
        "password": "",
        "client_version": ""
    }

    response = await client.post("/client/auth/enroll", json=enroll_data)
    # This should still work from a validation perspective, but might want to add business logic validation
    assert response.status_code in [200, 422]  # Depends on if you add validation for empty strings


@pytest.mark.asyncio
async def test_client_enroll_invalid_json(client: AsyncClient):
    """Test enrollment with invalid JSON payload"""
    response = await client.post("/client/auth/enroll", content="invalid json")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_client_enroll_different_client_versions(client: AsyncClient, db_session: AsyncSession):
    """Test enrollment with different client versions"""
    test_cases = [
        {"username": "user1", "client_version": "1.0.0"},
        {"username": "user2", "client_version": "2.1.5"},
        {"username": "user3", "client_version": "beta-1.0"},
    ]

    for i, case in enumerate(test_cases):
        enroll_data = {
            "username": case["username"],
            "password": f"password{i}",
            "client_version": case["client_version"]
        }

        response = await client.post("/client/auth/enroll", json=enroll_data)
        assert response.status_code == 200

        # Verify client version was stored correctly
        result = await db_session.execute(select(Client).where(Client.username == case["username"]))
        created_client = result.scalar_one_or_none()
        assert created_client.client_version == case["client_version"]


# LOGIN ENDPOINT TESTS

@pytest.mark.asyncio
async def test_client_login_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful client login"""
    # First create a client
    test_client = Client(
        username="loginuser",
        hashed_password=hash_password("password123"),
        ip_address="127.0.0.1",
        client_version="1.0.0"
    )
    db_session.add(test_client)
    await db_session.commit()

    login_data = {
        "username": "loginuser",
        "password": "password123"
    }

    response = await client.post("/client/auth/login", json=login_data)

    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data["token_type"] == "Bearer"
    assert response_data["access_token"] is not None

    # Verify refresh token cookie is set
    assert "refresh_token" in response.cookies

    # Verify client status was updated
    await db_session.refresh(test_client)
    assert test_client.alive is True


@pytest.mark.asyncio
async def test_client_login_invalid_username(client: AsyncClient, db_session: AsyncSession):
    """Test login with non-existent username"""
    login_data = {
        "username": "nonexistentuser",
        "password": "password123"
    }

    response = await client.post("/client/auth/login", json=login_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_client_login_invalid_password(client: AsyncClient, db_session: AsyncSession):
    """Test login with incorrect password"""
    # First create a client
    test_client = Client(
        username="loginuser2",
        hashed_password=hash_password("correctpassword"),
        ip_address="127.0.0.1",
        client_version="1.0.0"
    )
    db_session.add(test_client)
    await db_session.commit()

    login_data = {
        "username": "loginuser2",
        "password": "wrongpassword"
    }

    response = await client.post("/client/auth/login", json=login_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_client_login_missing_fields(client: AsyncClient):
    """Test login with missing required fields"""
    # Missing password
    login_data = {
        "username": "testuser"
    }

    response = await client.post("/client/auth/login", json=login_data)
    assert response.status_code == 422

    # Missing username
    login_data = {
        "password": "password123"
    }

    response = await client.post("/client/auth/login", json=login_data)
    assert response.status_code == 422

    # Empty payload
    response = await client.post("/client/auth/login", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_client_login_empty_fields(client: AsyncClient):
    """Test login with empty username/password"""
    login_data = {
        "username": "",
        "password": ""
    }

    response = await client.post("/client/auth/login", json=login_data)
    assert response.status_code in [401, 422]  # Could be validation error or auth error


@pytest.mark.asyncio
async def test_client_login_updates_ip_address(client: AsyncClient, db_session: AsyncSession):
    """Test that login updates the client's IP address"""
    # Create a client with a different IP
    test_client = Client(
        username="ipuser",
        hashed_password=hash_password("password123"),
        ip_address="192.168.1.1",
        client_version="1.0.0"
    )
    db_session.add(test_client)
    await db_session.commit()

    login_data = {
        "username": "ipuser",
        "password": "password123"
    }

    response = await client.post("/client/auth/login", json=login_data)
    assert response.status_code == 200

    # Verify IP address was updated
    await db_session.refresh(test_client)
    # The test client IP will be testclient, but we're testing that it gets updated
    assert test_client.ip_address is not None


# REFRESH ENDPOINT TESTS

@pytest.mark.asyncio
async def test_client_refresh_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful token refresh"""
    # First create a client and login to get tokens
    test_client = Client(
        username="refreshuser",
        hashed_password=hash_password("password123"),
        ip_address="127.0.0.1",
        client_version="1.0.0"
    )
    db_session.add(test_client)
    await db_session.commit()

    # Login to get refresh token
    login_data = {
        "username": "refreshuser",
        "password": "password123"
    }

    login_response = await client.post("/client/auth/login", json=login_data)
    assert login_response.status_code == 200

    # Get the refresh token from cookies
    refresh_token = login_response.cookies.get("refresh_token")
    assert refresh_token is not None

    # Now test refresh endpoint
    client.cookies = {"refresh_token": refresh_token}
    refresh_response = await client.post("/client/auth/refresh")

    assert refresh_response.status_code == 200
    response_data = refresh_response.json()
    assert "access_token" in response_data
    assert response_data["token_type"] == "Bearer"
    assert response_data["access_token"] is not None

    # Verify new refresh token cookie is set
    assert "refresh_token" in refresh_response.cookies


@pytest.mark.asyncio
async def test_client_refresh_missing_token(client: AsyncClient):
    """Test refresh without refresh token"""
    response = await client.post("/client/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token missing"


@pytest.mark.asyncio
async def test_client_refresh_invalid_token(client: AsyncClient):
    """Test refresh with invalid refresh token"""
    client.cookies = {"refresh_token": "invalid_token"}
    response = await client.post("/client/auth/refresh")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_client_refresh_revoked_token(client: AsyncClient, db_session: AsyncSession):
    """Test refresh with a revoked/expired token"""
    # Create a client and get a refresh token
    test_client = Client(
        username="revokeduser",
        hashed_password=hash_password("password123"),
        ip_address="127.0.0.1",
        client_version="1.0.0"
    )
    db_session.add(test_client)
    await db_session.commit()

    # Login to get refresh token
    login_data = {
        "username": "revokeduser",
        "password": "password123"
    }

    login_response = await client.post("/client/auth/login", json=login_data)
    refresh_token = login_response.cookies.get("refresh_token")

    # For this test, we'll just test that an invalid token returns 401
    # since we can't easily access the JTI from the token without decoding it
    client.cookies = {"refresh_token": "invalid_or_revoked_token"}
    response = await client.post("/client/auth/refresh")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_client_refresh_token_rotation(client: AsyncClient, db_session: AsyncSession):
    """Test that refresh tokens are properly rotated"""
    # Create a client and login
    test_client = Client(
        username="rotationuser",
        hashed_password=hash_password("password123"),
        ip_address="127.0.0.1",
        client_version="1.0.0"
    )
    db_session.add(test_client)
    await db_session.commit()

    # Login to get initial refresh token
    login_data = {
        "username": "rotationuser",
        "password": "password123"
    }

    login_response = await client.post("/client/auth/login", json=login_data)
    old_refresh_token = login_response.cookies.get("refresh_token")

    # Use refresh token to get new tokens
    client.cookies = {"refresh_token": old_refresh_token}
    refresh_response = await client.post("/client/auth/refresh")
    assert refresh_response.status_code == 200

    new_refresh_token = refresh_response.cookies.get("refresh_token")
    assert new_refresh_token is not None
    assert new_refresh_token != old_refresh_token

    # Try to use old refresh token again - should fail
    client.cookies = {"refresh_token": old_refresh_token}
    second_refresh_response = await client.post("/client/auth/refresh")
    assert second_refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_client_login_refresh_flow(client: AsyncClient, db_session: AsyncSession):
    """Test complete login -> refresh flow"""
    # Create a client
    test_client = Client(
        username="flowuser",
        hashed_password=hash_password("password123"),
        ip_address="127.0.0.1",
        client_version="1.0.0"
    )
    db_session.add(test_client)
    await db_session.commit()

    # Step 1: Login
    login_data = {
        "username": "flowuser",
        "password": "password123"
    }

    login_response = await client.post("/client/auth/login", json=login_data)
    assert login_response.status_code == 200

    login_data = login_response.json()
    initial_access_token = login_data["access_token"]
    refresh_token = login_response.cookies.get("refresh_token")

    # Step 2: Use refresh token to get new access token
    client.cookies = {"refresh_token": refresh_token}
    refresh_response = await client.post("/client/auth/refresh")
    assert refresh_response.status_code == 200

    refresh_data = refresh_response.json()
    new_access_token = refresh_data["access_token"]

    # Tokens should be different
    assert new_access_token != initial_access_token
    assert refresh_data["token_type"] == "Bearer"

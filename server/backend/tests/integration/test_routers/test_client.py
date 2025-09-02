import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_client_get_all(client: AsyncClient):
    # Populate database with some clients
    clients_data = [
        {
            "username": "client1",
            "password": "testpass1",
            "ip_address": "127.0.0.1",
            "client_version": "1.0.0"
        },
        {
            "username": "client2",
            "password": "testpass2",
            "ip_address": "127.0.0.1",
            "client_version": "1.0.0"
        },
        {
            "username": "client3",
            "password": "testpass3",
            "ip_address": "127.0.0.1",
            "client_version": "1.0.0"
        }
    ]

    # Enroll each client
    for client_data in clients_data:
        response = await client.post("/client/auth/enroll", json=client_data)
        assert response.status_code == 200

    # Authenticate
    auth_data = {
        "username": "user1",
        "password": "password123"
    }

    response = await client.post("/user/auth/register", json=auth_data)
    assert response.status_code == 200
    response = await client.post("/user/auth/login", json=auth_data)
    assert response.status_code == 200

    # Get access token and set Authorization header
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    client.headers["Authorization"] = f"Bearer {access_token}"

    # Test getting all clients
    response = await client.get("/client/all")
    assert response.status_code == 200

    response_data = response.json()
    clients_list = response_data['clients']
    assert len(clients_list) >= 3

    # Verify that our test clients are in the response
    usernames = [client["username"] for client in clients_list]
    assert "client1" in usernames
    assert "client2" in usernames
    assert "client3" in usernames

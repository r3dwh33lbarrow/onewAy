from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module import Module


async def ensure_user_logged_in(
    client: AsyncClient, username: str | None = None, password: str = "pw"
) -> tuple[str, str]:
    if username is None:
        username = f"user_{uuid4().hex[:8]}"

    register_response = await client.post(
        "/user/auth/register", json={"username": username, "password": password}
    )
    assert register_response.status_code in (200, 409)

    login_response = await client.post(
        "/user/auth/login", json={"username": username, "password": password}
    )
    assert login_response.status_code == 200
    assert login_response.json() == {"result": "success"}
    return username, password


async def enroll_and_login_client(
    client: AsyncClient,
    username: str | None = None,
    password: str = "pw",
    version: str = "1.0.0",
) -> tuple[str, dict[str, str]]:
    if username is None:
        username = f"client_{uuid4().hex[:8]}"

    enroll_response = await client.post(
        "/client/auth/enroll",
        json={"username": username, "password": password, "client_version": version},
    )
    assert enroll_response.status_code == 200

    login_response = await client.post(
        "/client/auth/login", json={"username": username, "password": password}
    )
    assert login_response.status_code == 200
    payload = login_response.json()
    token = payload["access_token"]
    headers = {"Authorization": f"Bearer {token}", "user-agent": "oneway-client"}
    return username, headers


@pytest.mark.asyncio
async def test_module_bucket_lifecycle(client: AsyncClient, db_session: AsyncSession):
    client.cookies.clear()

    # Create a module with no bucket
    m = Module(
        name="bucket_mod",
        description="test bucket",
        version="1.0.0",
        start="manual",
        binaries={},
    )
    db_session.add(m)
    await db_session.commit()

    user_username, _ = await ensure_user_logged_in(client)

    # Create new bucket
    r = await client.post("/module/new-bucket", params={"module_name": "bucket_mod"})
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    # Initially empty data
    r = await client.get("/module/bucket", params={"module_name": "bucket_mod"})
    assert r.status_code == 200
    payload = r.json()
    assert payload["module_name"] == "bucket_mod"
    assert payload["entries"] == []

    client_username, client_headers = await enroll_and_login_client(client)

    # Append data
    r = await client.put(
        "/module/bucket",
        params={"module_name": "bucket_mod"},
        headers=client_headers,
        json={"data": "hello"},
    )
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    r = await client.get("/module/bucket", params={"module_name": "bucket_mod"})
    assert r.status_code == 200
    data = r.json()
    assert data["module_name"] == "bucket_mod"
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert entry["client_username"] == client_username
    assert "hello" in entry["data"]
    assert entry["consumed"] is True

    # Append again and verify concatenation
    r = await client.put(
        "/module/bucket",
        params={"module_name": "bucket_mod"},
        headers=client_headers,
        json={"data": " world"},
    )
    assert r.status_code == 200

    r = await client.get("/module/bucket", params={"module_name": "bucket_mod"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert "hello" in entry["data"]
    assert "world" in entry["data"]

    # Delete the bucket
    await ensure_user_logged_in(client, user_username)
    r = await client.delete("/module/bucket", params={"module_name": "bucket_mod"})
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    # Access after deletion should fail with no bucket
    r = await client.get("/module/bucket", params={"module_name": "bucket_mod"})
    assert r.status_code == 400
    assert r.json()["detail"] == "No bucket exists for module"


@pytest.mark.asyncio
async def test_module_bucket_conflicts_and_errors(
    client: AsyncClient, db_session: AsyncSession
):
    client.cookies.clear()

    # Create a module
    m = Module(
        name="conflict_mod",
        description="conflict",
        version="0.1.0",
        start="manual",
        binaries={},
    )
    db_session.add(m)
    await db_session.commit()

    await ensure_user_logged_in(client, "user2", "pw")

    # Creating bucket the first time succeeds
    r = await client.post("/module/new-bucket", params={"module_name": "conflict_mod"})
    assert r.status_code == 200

    # Creating it again returns 400 conflict
    r = await client.post("/module/new-bucket", params={"module_name": "conflict_mod"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Bucket for module already exists"

    # Unknown module returns 404 for new-bucket
    r = await client.post("/module/new-bucket", params={"module_name": "no_such"})
    assert r.status_code == 404
    assert r.json()["detail"] == "Module not found"

    # Unknown module returns 404 for get
    r = await client.get("/module/bucket", params={"module_name": "no_such"})
    assert r.status_code == 404
    assert r.json()["detail"] == "Module not found"


@pytest.mark.asyncio
async def test_module_bucket_get_without_existing_bucket(
    client: AsyncClient, db_session: AsyncSession
):
    client.cookies.clear()

    # Module exists but has no bucket yet
    m = Module(
        name="nobucket_mod",
        description="nb",
        version="1.2.3",
        start="manual",
        binaries={},
    )
    db_session.add(m)
    await db_session.commit()

    await ensure_user_logged_in(client, "user3", "pw")

    r = await client.get("/module/bucket", params={"module_name": "nobucket_mod"})
    assert r.status_code == 400
    assert r.json()["detail"] == "No bucket exists for module"

    # Put should also fail due to missing bucket
    _, client_headers = await enroll_and_login_client(client)
    r = await client.put(
        "/module/bucket",
        params={"module_name": "nobucket_mod"},
        headers=client_headers,
        json={"data": "x"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "No bucket exists for module"

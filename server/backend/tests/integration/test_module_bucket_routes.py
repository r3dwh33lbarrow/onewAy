import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module import Module


async def _user_headers(
    client: AsyncClient, username: str = "admin", password: str = "pw"
):
    await client.post(
        "/user/auth/register", json={"username": username, "password": password}
    )
    r = await client.post(
        "/user/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    access_cookie = r.cookies.get("access_token")
    if not access_cookie:
        set_cookie = r.headers.get("set-cookie")
        if set_cookie and "access_token=" in set_cookie:
            access_cookie = set_cookie.split("access_token=")[1].split(";")[0]
    assert access_cookie
    return {"Authorization": f"Bearer {access_cookie}"}


@pytest.mark.asyncio
async def test_module_bucket_lifecycle(client: AsyncClient, db_session: AsyncSession):
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

    headers = await _user_headers(client)

    # Create new bucket
    r = await client.post(
        "/module/new-bucket", params={"module_name": "bucket_mod"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    # Initially empty data
    r = await client.get(
        "/module/bucket", params={"module_name": "bucket_mod"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json() == {"data": ""}

    # Append data
    r = await client.put(
        "/module/bucket",
        params={"module_name": "bucket_mod"},
        headers=headers,
        json={"data": "hello"},
    )
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    r = await client.get(
        "/module/bucket", params={"module_name": "bucket_mod"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json() == {"data": "hello"}

    # Append again and verify concatenation
    r = await client.put(
        "/module/bucket",
        params={"module_name": "bucket_mod"},
        headers=headers,
        json={"data": " world"},
    )
    assert r.status_code == 200

    r = await client.get(
        "/module/bucket", params={"module_name": "bucket_mod"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json() == {"data": "hello world"}

    # Delete the bucket
    r = await client.delete(
        "/module/bucket", params={"module_name": "bucket_mod"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    # Access after deletion should fail with no bucket
    r = await client.get(
        "/module/bucket", params={"module_name": "bucket_mod"}, headers=headers
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "No bucket exists for module"


@pytest.mark.asyncio
async def test_module_bucket_conflicts_and_errors(
    client: AsyncClient, db_session: AsyncSession
):
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

    headers = await _user_headers(client, "user2", "pw")

    # Creating bucket the first time succeeds
    r = await client.post(
        "/module/new-bucket", params={"module_name": "conflict_mod"}, headers=headers
    )
    assert r.status_code == 200

    # Creating it again returns 400 conflict
    r = await client.post(
        "/module/new-bucket", params={"module_name": "conflict_mod"}, headers=headers
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Bucket for module already exists"

    # Unknown module returns 404 for new-bucket
    r = await client.post(
        "/module/new-bucket", params={"module_name": "no_such"}, headers=headers
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Module not found"

    # Unknown module returns 404 for get
    r = await client.get(
        "/module/bucket", params={"module_name": "no_such"}, headers=headers
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Module not found"


@pytest.mark.asyncio
async def test_module_bucket_get_without_existing_bucket(
    client: AsyncClient, db_session: AsyncSession
):
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

    headers = await _user_headers(client, "user3", "pw")

    r = await client.get(
        "/module/bucket", params={"module_name": "nobucket_mod"}, headers=headers
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "No bucket exists for module"

    # Put should also fail due to missing bucket
    r = await client.put(
        "/module/bucket",
        params={"module_name": "nobucket_mod"},
        headers=headers,
        json={"data": "x"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "No bucket exists for module"

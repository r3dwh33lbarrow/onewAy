import io
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
async def test_module_upload_and_query_dir(client: AsyncClient):
    client.cookies.clear()
    await ensure_user_logged_in(client, "upload_admin")

    config_bytes = (
        b"name: test_upload\n"
        b"version: 0.1.0\n"
        b"start: manual\n"
        b"binaries:\n"
        b"  linux: binaries/linux/test_upload\n"
    )

    files = [
        (
            "files",
            (
                "config.yaml",
                config_bytes,
                "application/x-yaml",
            ),
        )
    ]

    r = await client.put("/module/upload", files=files)
    assert r.status_code == 200
    data = r.json()
    assert data["result"] == "success"
    assert "files_saved" in data
    assert "config.yaml" in data["files_saved"]

    r = await client.get("/module/query-module-dir")
    assert r.status_code == 200
    contents = r.json()["contents"]
    assert any("config.yaml" in str(x.get("file", "")) for x in contents)


@pytest.mark.asyncio
async def test_module_upload_invalid_path(client: AsyncClient):
    client.cookies.clear()
    await ensure_user_logged_in(client, "upload_invalid")

    files = [
        (
            "files",
            (
                "../evil.txt",
                b"bad",
                "text/plain",
            ),
        )
    ]
    r = await client.put("/module/upload", files=files)
    assert r.status_code == 400
    assert "Invalid file path" in r.json()["detail"]


@pytest.mark.asyncio
async def test_module_get_set_installed_and_conflicts(
    client: AsyncClient, db_session: AsyncSession
):
    client.cookies.clear()

    m = Module(
        name="demo_module",
        description="demo",
        version="1.0.0",
        start="manual",
        binaries={"linux": "demo"},
    )
    db_session.add(m)
    await db_session.commit()

    user_username, user_password = await ensure_user_logged_in(client, "module_admin")
    client_username, _ = await enroll_and_login_client(client, "c1")

    # Re-establish user session after client login
    await ensure_user_logged_in(client, user_username, user_password)

    r = await client.get("/module/get/demo_module")
    assert r.status_code == 200
    assert r.json()["name"] == "demo_module"

    r = await client.post(
        f"/module/set-installed/{client_username}",
        params={"module_name": "demo_module"},
    )
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    r = await client.post(
        f"/module/set-installed/{client_username}",
        params={"module_name": "demo_module"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_module_run_and_delete(client: AsyncClient, db_session: AsyncSession):
    client.cookies.clear()

    m = Module(
        name="run_delete",
        description="x",
        version="0.1",
        start="manual",
        binaries={},
    )
    db_session.add(m)
    await db_session.commit()

    user_username, user_password = await ensure_user_logged_in(client, "runner_admin")
    client_username, client_headers = await enroll_and_login_client(client, "runner")

    await ensure_user_logged_in(client, user_username, user_password)

    await client.post(
        f"/module/set-installed/{client_username}",
        params={"module_name": "run_delete"},
    )

    await ensure_user_logged_in(client, user_username, user_password)
    r = await client.get(
        f"/module/run/run_delete",
        params={"client_username": client_username},
    )
    assert r.status_code in (200, 500)

    await ensure_user_logged_in(client, user_username, user_password)
    r = await client.delete("/module/delete/run_delete")
    assert r.status_code == 200
    assert r.json() == {"result": "success"}


@pytest.mark.asyncio
async def test_module_installed_not_found(client: AsyncClient):
    client.cookies.clear()
    await ensure_user_logged_in(client, "installed_not_found")

    r = await client.get("/module/installed/nosuch")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_module_add_from_local_path_and_list_all(client: AsyncClient):
    client.cookies.clear()
    await ensure_user_logged_in(client, "modadder")

    r = await client.put("/module/add", json={"module_path": "test_module"})
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    r = await client.get("/module/all")
    assert r.status_code == 200
    names = [m["name"] for m in r.json()["modules"]]
    assert "test_module" in names


@pytest.mark.asyncio
async def test_module_add_nonexistent_path_returns_400(client: AsyncClient):
    client.cookies.clear()
    await ensure_user_logged_in(client, "modadder2")

    r = await client.put(
        "/module/add", json={"module_path": "does_not_exist_dir"}
    )
    assert r.status_code == 400
    assert "Module path does not exist" in r.json()["detail"]


@pytest.mark.asyncio
async def test_module_update_not_found_returns_404(client: AsyncClient):
    client.cookies.clear()
    await ensure_user_logged_in(client, "upduser")
    files = {
        "files": ("config.yaml", io.BytesIO(b"name: x\nversion: 0.1\nstart: manual\n"))
    }
    r = await client.put(
        "/module/update/no_such_module", files=files
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Module not found"


@pytest.mark.asyncio
async def test_module_installed_list_includes_set_item(
    client: AsyncClient, db_session: AsyncSession
):
    client.cookies.clear()

    m = Module(
        name="listed_mod", description="d", version="1.0.0", start="manual", binaries={}
    )
    db_session.add(m)
    await db_session.commit()

    user_username, user_password = await ensure_user_logged_in(client, "install_admin")
    client_username, client_headers = await enroll_and_login_client(client, "instclient")

    await ensure_user_logged_in(client, user_username, user_password)
    r = await client.post(
        f"/module/set-installed/{client_username}",
        params={"module_name": "listed_mod"},
    )
    assert r.status_code == 200

    await ensure_user_logged_in(client, user_username, user_password)
    r = await client.get(f"/module/installed/{client_username}")
    assert r.status_code == 200
    items = r.json()["all_installed"]
    assert any(it.get("name") == "listed_mod" for it in items)

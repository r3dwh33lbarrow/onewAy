import pytest
import io
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.module import Module


async def _client_headers(client: AsyncClient, username="modclient", password="pw", version="1.0.0"):
    await client.post(
        "/client/auth/enroll",
        json={"username": username, "password": password, "client_version": version},
    )
    r = await client.post("/client/auth/login", json={"username": username, "password": password})
    data = r.json()
    assert "access_token" in data
    return {"Authorization": f"Bearer {data['access_token']}", "user-agent": "oneway-client"}


async def _user_headers(client: AsyncClient, username="admin", password="pw"):
    await client.post("/user/auth/register", json={"username": username, "password": password})
    r = await client.post("/user/auth/login", json={"username": username, "password": password})
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
async def test_module_upload_and_query_dir(client: AsyncClient):
    headers = await _user_headers(client)
    files = {"files": ("config.yaml", b"name: test_upload\nversion: 0.1.0\nstart: manual\n")}
    r = await client.put("/module/upload", headers=headers, files=files)
    assert r.status_code == 200
    data = r.json()
    assert data["result"] == "success"
    assert "files_saved" in data
    assert "config.yaml" in data["files_saved"]

    r = await client.get("/module/query-module-dir", headers=headers)
    assert r.status_code == 200
    contents = r.json()["contents"]
    assert any("config.yaml" in str(x.get("file", "")) for x in contents)


@pytest.mark.asyncio
async def test_module_upload_invalid_path(client: AsyncClient):
    headers = await _user_headers(client)
    files = {"files": ("../evil.txt", b"bad")}
    r = await client.put("/module/upload", headers=headers, files=files)
    assert r.status_code == 400
    assert "Invalid file path" in r.json()["detail"]


@pytest.mark.asyncio
async def test_module_get_set_installed_and_conflicts(client: AsyncClient, db_session: AsyncSession):
    m = Module(
        name="demo_module",
        description="demo",
        version="1.0.0",
        start="manual",
        binaries={"linux": "demo"},
    )
    db_session.add(m)
    await db_session.commit()

    headers = await _client_headers(client, "c1", "pw")

    r = await client.get("/module/get/demo_module", headers=headers)
    assert r.status_code == 200
    assert r.json()["name"] == "demo_module"

    r = await client.post("/module/set-installed/c1", params={"module_name": "demo_module"}, headers=headers)
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    r = await client.post("/module/set-installed/c1", params={"module_name": "demo_module"}, headers=headers)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_module_run_and_delete(client: AsyncClient, db_session: AsyncSession):
    m = Module(
        name="run_delete",
        description="x",
        version="0.1",
        start="manual",
        binaries={},
    )
    db_session.add(m)
    await db_session.commit()

    user_headers = await _user_headers(client)
    client_headers = await _client_headers(client, "runner", "pw")

    await client.post("/module/set-installed/runner", params={"module_name": "run_delete"}, headers=client_headers)

    r = await client.get("/module/run/run_delete", params={"client_username": "runner"}, headers=user_headers)
    assert r.status_code in (200, 500)

    r = await client.delete("/module/delete/run_delete", headers=user_headers)
    assert r.status_code == 200
    assert r.json() == {"result": "success"}


@pytest.mark.asyncio
async def test_module_installed_not_found(client: AsyncClient):
    headers = await _client_headers(client)
    r = await client.get("/module/installed/nosuch", headers=headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_module_add_from_local_path_and_list_all(client: AsyncClient):
    user_headers = await _user_headers(client, "modadder", "pw")
    r = await client.put("/module/add", headers=user_headers, json={"module_path": "test_module"})
    assert r.status_code == 200
    assert r.json() == {"result": "success"}

    client_headers = await _client_headers(client, "listcaller", "pw")
    r = await client.get("/module/all", headers=client_headers)
    assert r.status_code == 200
    names = [m["name"] for m in r.json()["modules"]]
    assert "test_module" in names


@pytest.mark.asyncio
async def test_module_add_nonexistent_path_returns_400(client: AsyncClient):
    user_headers = await _user_headers(client, "modadder2", "pw")
    r = await client.put("/module/add", headers=user_headers, json={"module_path": "does_not_exist_dir"})
    assert r.status_code == 400
    assert "Module path does not exist" in r.json()["detail"]


@pytest.mark.asyncio
async def test_module_update_not_found_returns_404(client: AsyncClient):
    user_headers = await _user_headers(client, "upduser", "pw")
    files = {"files": ("config.yaml", io.BytesIO(b"name: x\nversion: 0.1\nstart: manual\n"))}
    r = await client.put("/module/update/no_such_module", headers=user_headers, files=files)
    assert r.status_code == 404
    assert r.json()["detail"] == "Module not found"


@pytest.mark.asyncio
async def test_module_installed_list_includes_set_item(client: AsyncClient, db_session: AsyncSession):
    m = Module(name="listed_mod", description="d", version="1.0.0", start="manual", binaries={})
    db_session.add(m)
    await db_session.commit()

    client_headers = await _client_headers(client, "instclient", "pw")
    r = await client.post("/module/set-installed/instclient", params={"module_name": "listed_mod"}, headers=client_headers)
    assert r.status_code == 200

    r = await client.get("/module/installed/instclient", headers=client_headers)
    assert r.status_code == 200
    items = r.json()
    assert any(it.get("name") == "listed_mod" for it in items)

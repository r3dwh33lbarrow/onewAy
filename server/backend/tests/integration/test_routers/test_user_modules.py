import io
import json
import zipfile
import pytest
import shutil
import os
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.module import Module


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

async def auth_client(client: AsyncClient, username="tester", password="password123") -> AsyncClient:
    """Register + login a test user and set access_token in Authorization header."""
    # Register
    reg_resp = await client.post("/user/auth/register", json={"username": username, "password": password})
    assert reg_resp.status_code in [200, 409]  # user may already exist

    # Login
    login_resp = await client.post("/user/auth/login", json={"username": username, "password": password})
    assert login_resp.status_code == 200
    access_token = login_resp.cookies.get("access_token")
    assert access_token is not None
    # Set Authorization header instead of cookie
    client.headers["Authorization"] = f"Bearer {access_token}"
    return client


def make_zip_with_config(config: dict, corrupt: bool = False) -> io.BytesIO:
    """Create an in-memory zip file containing config.yaml."""
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        if corrupt:
            zf.writestr("config.yaml", "::: not yaml :::")
        else:
            zf.writestr("config.yaml", json.dumps(config))
    zip_bytes.seek(0)
    return zip_bytes


def cleanup_test_modules():
    """Clean up test module directories."""
    mod_dir = Path(__file__).resolve().parent.parent.parent / "app" / "modules"
    if mod_dir.exists():
        for item in mod_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)


@pytest.fixture(autouse=True)
async def cleanup_before_each_test():
    """Automatically cleanup before each test."""
    cleanup_test_modules()
    yield
    cleanup_test_modules()


# --------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_modules_all_empty(client: AsyncClient):
    client = await auth_client(client)
    response = await client.get("/user/modules/all")
    assert response.status_code == 200
    assert response.json() == {"modules": []}


@pytest.mark.asyncio
async def test_user_modules_add_missing_path(client: AsyncClient):
    client = await auth_client(client)
    response = await client.post("/user/modules/add", json={"module_path": "/does/not/exist"})
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


# ---------- UPLOAD TESTS ----------

@pytest.mark.asyncio
async def test_user_modules_upload_and_add(client: AsyncClient, db_session: AsyncSession):
    client = await auth_client(client)
    module_name = "UploadModule"
    config = {
        "name": module_name,
        "description": "Upload test module",
        "version": "1.0.0",
        "start": "main.py",
        "binaries": json.dumps({"linux": "bin"})
    }
    zip_bytes = make_zip_with_config(config)
    files = {"file": ("module.zip", zip_bytes, "application/zip")}

    response = await client.post(f"/user/modules/upload?dev_name={module_name}", files=files)
    assert response.status_code == 200  # direct success response
    assert response.json()["result"] == "success"

    # The module name gets converted to snake_case, so "UploadModule" becomes "uploadmodule"
    result = await db_session.execute(select(Module).where(Module.name == "uploadmodule"))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename, content, expected_detail",
    [
        ("bad.txt", b"not a zip", "File must be a ZIP archive"),
        ("bad.zip", b"not-a-real-zip", "Invalid ZIP file"),
    ],
)
async def test_user_modules_upload_invalid_files(client: AsyncClient, filename, content, expected_detail):
    client = await auth_client(client)
    files = {"file": (filename, io.BytesIO(content), "application/octet-stream")}
    response = await client.post("/user/modules/upload?dev_name=Invalid", files=files)
    assert response.status_code == 400
    assert expected_detail in response.json()["detail"]


@pytest.mark.asyncio
async def test_user_modules_upload_missing_config_yaml(client: AsyncClient):
    client = await auth_client(client)
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("other.txt", "no config")
    zip_bytes.seek(0)

    files = {"file": ("nocfg.zip", zip_bytes, "application/zip")}
    response = await client.post("/user/modules/upload?dev_name=NoCfg", files=files)
    assert response.status_code == 400
    assert "config.yaml" in response.json()["detail"]


# ---------- GET TESTS ----------

@pytest.mark.asyncio
async def test_user_modules_get_success(client: AsyncClient, db_session: AsyncSession):
    client = await auth_client(client)
    mod = Module(name="getmod", description="desc", version="2.0", start="main.py", binaries={"win": "exe"})
    db_session.add(mod)
    await db_session.commit()

    response = await client.get("/user/modules/getmod")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "getmod"
    assert data["version"] == "2.0"
    assert "win" in data["binaries"]


@pytest.mark.asyncio
async def test_user_modules_get_not_found(client: AsyncClient):
    client = await auth_client(client)
    response = await client.get("/user/modules/doesnotexist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Module not found"


# ---------- UPDATE TESTS ----------

@pytest.mark.asyncio
async def test_user_modules_update_success(client: AsyncClient, db_session: AsyncSession):
    client = await auth_client(client)
    mod = Module(name="updateme", description="old", version="0.1", start="old_start.py", binaries={})
    db_session.add(mod)
    await db_session.commit()

    new_config = {
        "name": "UpdatedName",
        "description": "new description",
        "version": "1.2.3",
        "start": "new_start.py",
        "binaries": json.dumps({"linux": "newbin"})
    }
    zip_bytes = make_zip_with_config(new_config)
    files = {"file": ("update.zip", zip_bytes, "application/zip")}

    response = await client.put("/user/modules/update/updateme", files=files)
    assert response.status_code == 200
    assert response.json()["result"] == "success"

    await db_session.refresh(mod)
    # "UpdatedName" gets converted to "updatedname" (snake_case without underscores)
    assert mod.name == "updatedname"
    assert mod.version == "1.2.3"
    assert mod.description == "new description"


@pytest.mark.asyncio
async def test_user_modules_update_not_found(client: AsyncClient):
    client = await auth_client(client)
    fake_zip = make_zip_with_config({"name": "fake", "version": "1.0.0", "start": "main.py"})
    files = {"file": ("fake.zip", fake_zip, "application/zip")}
    response = await client.put("/user/modules/update/notreal", files=files)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "config, expected_msg",
    [
        ({"version": "1.0.0"}, "Missing required key"),  # no name
        ({"name": "BadMod"}, "Missing required key"),    # no version
    ],
)
async def test_user_modules_update_invalid_config(client: AsyncClient, db_session: AsyncSession, config, expected_msg):
    client = await auth_client(client)
    mod = Module(name="broken", description="old", version="0.1", start="old.py", binaries={})
    db_session.add(mod)
    await db_session.commit()

    zip_bytes = make_zip_with_config(config)
    files = {"file": ("bad.zip", zip_bytes, "application/zip")}
    response = await client.put("/user/modules/update/broken", files=files)

    assert response.status_code == 400
    assert expected_msg in response.json()["detail"]


@pytest.mark.asyncio
async def test_user_modules_update_corrupt_yaml(client: AsyncClient, db_session: AsyncSession):
    client = await auth_client(client)
    mod = Module(name="yamlmod", description="old", version="0.1", start="old.py", binaries={})
    db_session.add(mod)
    await db_session.commit()

    zip_bytes = make_zip_with_config({}, corrupt=True)
    files = {"file": ("corrupt.zip", zip_bytes, "application/zip")}
    response = await client.put("/user/modules/update/yamlmod", files=files)

    assert response.status_code == 400
    assert "Error parsing config.yaml" in response.json()["detail"]


# ---------- DELETE TESTS ----------

@pytest.mark.asyncio
async def test_user_modules_delete_success(client: AsyncClient, db_session: AsyncSession):
    client = await auth_client(client)
    mod = Module(name="deleteme", description="bye", version="9.9.9", start="main.py", binaries={})
    db_session.add(mod)
    await db_session.commit()

    response = await client.delete("/user/modules/delete/deleteme")
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "success"

    result = await db_session.execute(select(Module).where(Module.name == "deleteme"))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_user_modules_delete_not_found(client: AsyncClient):
    client = await auth_client(client)
    response = await client.delete("/user/modules/delete/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Module not found"


# ---------- SECURITY TESTS ----------

@pytest.mark.asyncio
async def test_user_modules_upload_path_traversal_attempt(client: AsyncClient):
    """Ensure upload rejects ZIP entries with path traversal attempts"""
    client = await auth_client(client)

    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("../evil.txt", "hacked!")   # malicious path
    zip_bytes.seek(0)

    files = {"file": ("evil.zip", zip_bytes, "application/zip")}
    response = await client.post("/user/modules/upload?dev_name=EvilMod", files=files)

    assert response.status_code == 400
    assert "Invalid file path" in response.json()["detail"]

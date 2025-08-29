
import os
import shutil
import zipfile
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module import Module
from app.models.user import User
from app.services.password import hash_password


@pytest.fixture(scope="function")
def test_module_path() -> Path:
    module_dir = Path(__file__).parent / "test_module"
    if not module_dir.exists():
        module_dir.mkdir()

    config_content = """
name: Test Module
description: A module for testing
binary_path: test_module.exe
lifecycle: on-start
path: test_module.exe
version: "0.1.0"
"""
    with open(module_dir / "config.yaml", "w") as f:
        f.write(config_content)

    with open(module_dir / "test_module.exe", "w") as f:
        f.write("dummy executable")

    yield module_dir

    if module_dir.exists():
        shutil.rmtree(module_dir)
    
    modules_dir = Path(__file__).parent.parent.parent.parent / "app" / "modules"
    if modules_dir.exists():
        shutil.rmtree(modules_dir)

@pytest.fixture(scope="function")
def test_module_zip(test_module_path: Path) -> Path:
    zip_path = test_module_path.parent / "test_module.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in test_module_path.glob('**/*'):
            zipf.write(file, file.relative_to(test_module_path))

    yield zip_path

    if zip_path.exists():
        os.remove(zip_path)


@pytest.mark.asyncio
async def test_get_all_modules_unauthenticated(client: AsyncClient):
    response = await client.get("/user/modules/all")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_all_modules_authenticated_no_modules(client: AsyncClient, db_session: AsyncSession):
    # Create and login a user
    test_user = User(username="testuser", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()
    login_data = {"username": "testuser", "password": "password123"}
    login_response = await client.post("/user/auth/login", json=login_data)
    access_token = login_response.cookies.get("access_token")

    response = await client.get("/user/modules/all", cookies={"access_token": access_token})
    assert response.status_code == 200
    assert response.json() == {"modules": []}


@pytest.mark.asyncio
async def test_add_module_success(client: AsyncClient, db_session: AsyncSession, test_module_path: Path):
    # Create and login a user
    test_user = User(username="testuser", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()
    login_data = {"username": "testuser", "password": "password123"}
    login_response = await client.post("/user/auth/login", json=login_data)
    access_token = login_response.cookies.get("access_token")

    response = await client.post(f"/user/modules/add?module_path={str(test_module_path)}", cookies={"access_token": access_token})
    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    # Verify the module was created in the database
    result = await db_session.execute(select(Module).where(Module.name == "test_module"))
    created_module = result.scalar_one_or_none()
    assert created_module is not None
    assert created_module.name == "test_module"
    assert created_module.version == "0.1.0"


@pytest.mark.asyncio
async def test_upload_module_success(client: AsyncClient, db_session: AsyncSession, test_module_zip: Path):
    # Create and login a user
    test_user = User(username="testuser", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()
    login_data = {"username": "testuser", "password": "password123"}
    login_response = await client.post("/user/auth/login", json=login_data)
    access_token = login_response.cookies.get("access_token")

    with open(test_module_zip, "rb") as f:
        files = {"file": ("test_module.zip", f, "application/zip")}
        response = await client.post("/user/modules/upload?dev_name=test_module", files=files, cookies={"access_token": access_token}, follow_redirects=False)

    assert response.status_code == 303

    # Follow the redirect
    redirect_url = response.headers["location"]
    response = await client.post(redirect_url, cookies={"access_token": access_token})

    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    # Verify the module was created in the database
    result = await db_session.execute(select(Module).where(Module.name == "test_module"))
    created_module = result.scalar_one_or_none()
    assert created_module is not None
    assert created_module.name == "test_module"
    assert created_module.version == "0.1.0"


@pytest.mark.asyncio
async def test_get_module_success(client: AsyncClient, db_session: AsyncSession, test_module_path: Path):
    # Create and login a user
    test_user = User(username="testuser", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()
    login_data = {"username": "testuser", "password": "password123"}
    login_response = await client.post("/user/auth/login", json=login_data)
    access_token = login_response.cookies.get("access_token")

    # Add a module first
    await client.post(f"/user/modules/add?module_path={str(test_module_path)}", cookies={"access_token": access_token})

    response = await client.get("/user/modules/test_module", cookies={"access_token": access_token})
    assert response.status_code == 200
    assert response.json()["name"] == "test_module"
    assert response.json()["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_delete_module_success(client: AsyncClient, db_session: AsyncSession, test_module_path: Path):
    # Create and login a user
    test_user = User(username="testuser", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()
    login_data = {"username": "testuser", "password": "password123"}
    login_response = await client.post("/user/auth/login", json=login_data)
    access_token = login_response.cookies.get("access_token")

    # Add a module first
    await client.post(f"/user/modules/add?module_path={str(test_module_path)}", cookies={"access_token": access_token})

    response = await client.delete("/user/modules/delete/test_module", cookies={"access_token": access_token})
    assert response.status_code == 200
    assert response.json()["result"] == "success"

    # Verify the module was deleted from the database
    result = await db_session.execute(select(Module).where(Module.name == "test_module"))
    deleted_module = result.scalar_one_or_none()
    assert deleted_module is None


@pytest.mark.asyncio
async def test_update_module_success(client: AsyncClient, db_session: AsyncSession, test_module_path: Path, test_module_zip: Path):
    # Create and login a user
    test_user = User(username="testuser", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()
    login_data = {"username": "testuser", "password": "password123"}
    login_response = await client.post("/user/auth/login", json=login_data)
    access_token = login_response.cookies.get("access_token")

    # Add a module first
    await client.post(f"/user/modules/add?module_path={str(test_module_path)}", cookies={"access_token": access_token})

    # Create a new version of the module
    module_dir = Path(__file__).parent / "test_module_v2"
    if not module_dir.exists():
        module_dir.mkdir()

    config_content = """
name: Test Module
description: A module for testing
binary_path: test_module.exe
lifecycle: on-start
path: test_module.exe
version: "0.2.0"
"""
    with open(module_dir / "config.yaml", "w") as f:
        f.write(config_content)

    with open(module_dir / "test_module.exe", "w") as f:
        f.write("dummy executable v2")

    zip_path = module_dir.parent / "test_module_v2.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in module_dir.glob('**/*'):
            zipf.write(file, file.relative_to(module_dir))

    with open(zip_path, "rb") as f:
        files = {"file": ("test_module_v2.zip", f, "application/zip")}
        response = await client.put("/user/modules/update/test_module", files=files, cookies={"access_token": access_token})

    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    # Verify the module was updated in the database
    result = await db_session.execute(select(Module).where(Module.name == "test_module"))
    updated_module = result.scalar_one_or_none()
    assert updated_module is not None
    assert updated_module.version == "0.2.0"

    if module_dir.exists():
        shutil.rmtree(module_dir)
    if zip_path.exists():
        os.remove(zip_path)

import io
import json
import zipfile
from unittest.mock import patch

import pytest
import yaml
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.module import Module


@pytest.fixture
def sample_module_config():
    """Sample module configuration for testing"""
    return {
        "name": "Test Module",
        "description": "A test module for unit testing",
        "version": "1.0.0",
        "binaries": json.dumps({"linux": "test_binary_linux", "windows": "test_binary_windows.exe"})
    }


@pytest.fixture
def sample_zip_file(sample_module_config):
    """Create a sample ZIP file with config.yaml for testing"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add config.yaml to the zip
        config_content = yaml.dump(sample_module_config)
        zip_file.writestr("config.yaml", config_content)
        # Add a sample binary file
        zip_file.writestr("test_binary", "fake binary content")

    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def invalid_zip_file():
    """Create an invalid ZIP file for testing"""
    return io.BytesIO(b"This is not a valid ZIP file")


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Create authentication headers for testing"""
    # Register a test user
    register_data = {"username": "testuser", "password": "testpass123"}
    await client.post("/user/auth/register", json=register_data)

    # Login to get access token
    login_data = {"username": "testuser", "password": "testpass123"}
    login_response = await client.post("/user/auth/login", json=login_data)

    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def sample_module_in_db(db_session: AsyncSession):
    """Create a sample module in the database for testing"""
    module = Module(
        name="test_module",
        description="Test module description",
        version="1.0.0",
        binaries={"linux": "test_binary_linux", "windows": "test_binary_windows.exe"}
    )
    db_session.add(module)
    await db_session.commit()
    await db_session.refresh(module)
    return module


class TestUserModulesAll:
    """Test the GET /user/modules/all endpoint"""

    @pytest.mark.asyncio
    async def test_get_all_modules_empty(self, client: AsyncClient, auth_headers, db_session: AsyncSession):
        """Test getting all modules when database is empty"""
        response = await client.get("/user/modules/all", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "modules" in data
        assert data["modules"] == []

    @pytest.mark.asyncio
    async def test_get_all_modules_with_data(self, client: AsyncClient, auth_headers, db_session: AsyncSession, sample_module_in_db):
        """Test getting all modules when modules exist in database"""
        response = await client.get("/user/modules/all", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "modules" in data
        assert len(data["modules"]) == 1

        module = data["modules"][0]
        assert module["name"] == "test_module"
        assert module["version"] == "1.0.0"
        assert "binaries_platform" in module
        assert set(module["binaries_platform"]) == {"linux", "windows"}

    @pytest.mark.asyncio
    async def test_get_all_modules_unauthorized(self, client: AsyncClient, db_session: AsyncSession):
        """Test getting all modules without authentication"""
        response = await client.get("/user/modules/all")
        assert response.status_code == 401


class TestUserModulesAdd:
    """Test the POST /user/modules/add endpoint"""

    @pytest.mark.asyncio
    async def test_add_module_success(self, client: AsyncClient, auth_headers, db_session: AsyncSession, tmp_path, sample_module_config):
        """Test successfully adding a module"""
        # Create a temporary directory with config.yaml
        module_dir = tmp_path / "test_module"
        module_dir.mkdir()

        config_path = module_dir / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_module_config, f)

        response = await client.post(
            f"/user/modules/add?module_path={str(module_dir)}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json() == {"result": "success"}

        # Verify module was added to database
        result = await db_session.execute(select(Module).where(Module.name == "test_module"))
        module = result.scalar_one_or_none()
        assert module is not None
        assert module.name == "test_module"
        assert module.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_add_module_nonexistent_path(self, client: AsyncClient, auth_headers, db_session: AsyncSession):
        """Test adding a module with non-existent path"""
        response = await client.post(
            "/user/modules/add?module_path=/nonexistent/path",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Module path does not exist" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_module_missing_config(self, client: AsyncClient, auth_headers, db_session: AsyncSession, tmp_path):
        """Test adding a module without config.yaml"""
        module_dir = tmp_path / "test_module"
        module_dir.mkdir()

        response = await client.post(
            f"/user/modules/add?module_path={str(module_dir)}",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Module config.yaml does not exist" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_module_invalid_yaml(self, client: AsyncClient, auth_headers, db_session: AsyncSession, tmp_path):
        """Test adding a module with invalid YAML config"""
        module_dir = tmp_path / "test_module"
        module_dir.mkdir()

        config_path = module_dir / "config.yaml"
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: content: [")

        response = await client.post(
            f"/user/modules/add?module_path={str(module_dir)}",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Error parsing config.yaml" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_module_missing_required_keys(self, client: AsyncClient, auth_headers, db_session: AsyncSession, tmp_path):
        """Test adding a module with missing required keys in config"""
        module_dir = tmp_path / "test_module"
        module_dir.mkdir()

        config_path = module_dir / "config.yaml"
        incomplete_config = {"description": "Missing name and version"}
        with open(config_path, 'w') as f:
            yaml.dump(incomplete_config, f)

        response = await client.post(
            f"/user/modules/add?module_path={str(module_dir)}",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Missing required key in config.yaml" in response.json()["detail"]


class TestUserModulesUpload:
    """Test the POST /user/modules/upload endpoint"""

    @pytest.mark.asyncio
    async def test_upload_module_success(self, client: AsyncClient, auth_headers, db_session: AsyncSession, sample_zip_file):
        """Test successfully uploading a module"""
        files = {"file": ("test_module.zip", sample_zip_file, "application/zip")}

        with patch('app.routes.user_modules.RedirectResponse') as mock_redirect:
            mock_redirect.return_value.status_code = 303
            response = await client.post(
                "/user/modules/upload?dev_name=TestModule",
                headers=auth_headers,
                files=files
            )

        # The endpoint should redirect to add endpoint
        assert response.status_code == 200  # FastAPI test client follows redirects

    @pytest.mark.asyncio
    async def test_upload_module_existing_directory(self, client: AsyncClient, auth_headers, db_session: AsyncSession, sample_zip_file, tmp_path):
        """Test uploading a module when directory already exists"""
        # Create the directory first
        with patch('app.routes.user_modules.Path') as mock_path:
            mock_path.return_value = tmp_path / "TestModule"
            mock_path.return_value.mkdir()  # Create the directory

            files = {"file": ("test_module.zip", sample_zip_file, "application/zip")}
            response = await client.post(
                "/user/modules/upload?dev_name=TestModule",
                headers=auth_headers,
                files=files
            )

        assert response.status_code == 400
        assert "Module directory already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_non_zip_file(self, client: AsyncClient, auth_headers, db_session: AsyncSession):
        """Test uploading a non-ZIP file"""
        files = {"file": ("test_module.txt", io.BytesIO(b"not a zip file"), "text/plain")}

        response = await client.post(
            "/user/modules/upload?dev_name=TestModule",
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 400
        assert "File must be a ZIP archive" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_invalid_zip_file(self, client: AsyncClient, auth_headers, db_session: AsyncSession, invalid_zip_file):
        """Test uploading an invalid ZIP file"""
        files = {"file": ("invalid.zip", invalid_zip_file, "application/zip")}

        response = await client.post(
            "/user/modules/upload?dev_name=TestModule",
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 400
        assert "Invalid ZIP file" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_zip_without_config(self, client: AsyncClient, auth_headers, db_session: AsyncSession):
        """Test uploading a ZIP file without config.yaml"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("some_file.txt", "content")

        zip_buffer.seek(0)
        files = {"file": ("no_config.zip", zip_buffer, "application/zip")}

        response = await client.post(
            "/user/modules/upload?dev_name=TestModule",
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 400
        assert "Extracted module must contain config.yaml" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_zip_with_malicious_paths(self, client: AsyncClient, auth_headers, db_session: AsyncSession):
        """Test uploading a ZIP file with malicious file paths"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("../../../etc/passwd", "malicious content")
            zip_file.writestr("config.yaml", "name: test\nversion: 1.0.0")

        zip_buffer.seek(0)
        files = {"file": ("malicious.zip", zip_buffer, "application/zip")}

        response = await client.post(
            "/user/modules/upload?dev_name=TestModule",
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 400
        assert "Invalid file path in archive" in response.json()["detail"]


class TestUserModulesUpdate:
    """Test the PUT /user/modules/update/{module_name} endpoint"""

    @pytest.mark.asyncio
    async def test_update_module_success(self, client: AsyncClient, auth_headers, db_session: AsyncSession, sample_module_in_db, sample_zip_file):
        """Test successfully updating a module"""
        files = {"file": ("updated_module.zip", sample_zip_file, "application/zip")}

        response = await client.put(
            f"/user/modules/update/{sample_module_in_db.name}",
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 200
        assert response.json() == {"result": "success"}

        # Verify module was updated in database
        await db_session.refresh(sample_module_in_db)
        assert sample_module_in_db.name == "test_module"  # snake_case converted

    @pytest.mark.asyncio
    async def test_update_nonexistent_module(self, client: AsyncClient, auth_headers, db_session: AsyncSession, sample_zip_file):
        """Test updating a module that doesn't exist"""
        files = {"file": ("updated_module.zip", sample_zip_file, "application/zip")}

        response = await client.put(
            "/user/modules/update/nonexistent-module",
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 404
        assert "Module not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_module_invalid_zip(self, client: AsyncClient, auth_headers, db_session: AsyncSession, sample_module_in_db, invalid_zip_file):
        """Test updating a module with invalid ZIP file"""
        files = {"file": ("invalid.zip", invalid_zip_file, "application/zip")}

        response = await client.put(
            f"/user/modules/update/{sample_module_in_db.name}",
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 400
        assert "File must be a ZIP archive" in response.json()["detail"]


class TestUserModulesDelete:
    """Test the DELETE /user/modules/delete/{module_name} endpoint"""

    @pytest.mark.asyncio
    async def test_delete_module_success(self, client: AsyncClient, auth_headers, db_session: AsyncSession, sample_module_in_db):
        """Test successfully deleting a module"""
        response = await client.delete(
            f"/user/modules/delete/{sample_module_in_db.name}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "success"
        assert "deleted successfully" in data["message"]

        # Verify module was deleted from database
        result = await db_session.execute(select(Module).where(Module.name == sample_module_in_db.name))
        deleted_module = result.scalar_one_or_none()
        assert deleted_module is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_module(self, client: AsyncClient, auth_headers, db_session: AsyncSession):
        """Test deleting a module that doesn't exist"""
        response = await client.delete(
            "/user/modules/delete/nonexistent-module",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "Module not found" in response.json()["detail"]


class TestUserModulesGet:
    """Test the GET /user/modules/{module_name} endpoint"""

    @pytest.mark.asyncio
    async def test_get_module_success(self, client: AsyncClient, auth_headers, db_session: AsyncSession, sample_module_in_db):
        """Test successfully getting a specific module"""
        response = await client.get(
            f"/user/modules/{sample_module_in_db.name}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_module_in_db.name
        assert data["description"] == sample_module_in_db.description
        assert data["version"] == sample_module_in_db.version
        assert data["binaries"] == sample_module_in_db.binaries

    @pytest.mark.asyncio
    async def test_get_nonexistent_module(self, client: AsyncClient, auth_headers, db_session: AsyncSession):
        """Test getting a module that doesn't exist"""
        response = await client.get(
            "/user/modules/nonexistent-module",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "Module not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_module_unauthorized(self, client: AsyncClient, db_session: AsyncSession, sample_module_in_db):
        """Test getting a module without authentication"""
        response = await client.get(f"/user/modules/{sample_module_in_db.name}")
        assert response.status_code == 401


class TestUserModulesAuthenticationRequired:
    """Test that all endpoints require authentication"""

    @pytest.mark.asyncio
    async def test_all_endpoints_require_auth(self, client: AsyncClient, db_session: AsyncSession):
        """Test that all endpoints return 401 without authentication"""
        endpoints = [
            ("GET", "/user/modules/all"),
            ("POST", "/user/modules/add?module_path=/test"),
            ("POST", "/user/modules/upload?dev_name=test"),
            ("PUT", "/user/modules/update/test"),
            ("DELETE", "/user/modules/delete/test"),
            ("GET", "/user/modules/test"),
        ]

        for method, endpoint in endpoints:
            response = None
            if method == "GET":
                response = await client.get(endpoint)
            elif method == "POST":
                if "upload" in endpoint:
                    files = {"file": ("test.zip", io.BytesIO(b"fake"), "application/zip")}
                    response = await client.post(endpoint, files=files)
                else:
                    response = await client.post(endpoint)
            elif method == "PUT":
                files = {"file": ("test.zip", io.BytesIO(b"fake"), "application/zip")}
                response = await client.put(endpoint, files=files)
            elif method == "DELETE":
                response = await client.delete(endpoint)

            if response:
                assert response.status_code == 401, f"Endpoint {method} {endpoint} should require authentication"

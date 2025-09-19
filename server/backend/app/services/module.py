import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiofiles
import yaml
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.module import Module
from app.settings import settings
from app.utils import convert_to_snake_case


async def validate_file_path(filename: str) -> Path:
    """Validate and resolve file path within module directory."""
    if not filename:
        raise HTTPException(status_code=400, detail="File must have a filename")

    rel_path = Path(filename)

    if any(part in ["..", ".", ""] for part in rel_path.parts):
        raise HTTPException(
            status_code=400,
            detail="Invalid file path - no relative path traversal allowed",
        )

    try:
        dest_path = (Path(settings.paths.module_dir) / rel_path).resolve()

        if not str(dest_path).startswith(
            str(Path(settings.paths.module_dir).resolve())
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid file path - outside allowed directory",
            )
        return dest_path
    except Exception:
        raise HTTPException(status_code=400, detail="Unsafe file path")


def determine_module_directory(
    dest_path: Path, current_module_dir: Optional[Path]
) -> Path:
    """Determine the module directory based on file paths."""
    if current_module_dir is None:
        return dest_path.parent
    elif dest_path.parent != current_module_dir and not str(dest_path).startswith(
        str(current_module_dir)
    ):
        potential_module_dir = dest_path
        while potential_module_dir.parent != Path(settings.paths.module_dir):
            potential_module_dir = potential_module_dir.parent
        if current_module_dir != potential_module_dir:
            return potential_module_dir
    return current_module_dir


async def save_uploaded_file(file: UploadFile, dest_path: Path) -> None:
    """Save an uploaded file to the specified destination."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(dest_path, "wb") as out:
        while True:
            chunk = await file.read(1024)
            if not chunk:
                break
            await out.write(chunk)


async def process_uploaded_files(files: List[UploadFile]) -> Tuple[List[str], Path]:
    """Process uploaded files and return saved files list and module directory."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    saved = []
    module_dir = None

    for f in files:
        dest_path = await validate_file_path(f.filename)
        module_dir = determine_module_directory(dest_path, module_dir)

        await save_uploaded_file(f, dest_path)
        saved.append(str(dest_path.relative_to(settings.paths.module_dir)))

    if module_dir is None:
        raise HTTPException(status_code=400, detail="No files were processed")

    return saved, module_dir


async def load_config_yaml(config_path: Path) -> Dict:
    """Load and parse config.yaml file."""
    if not config_path.exists():
        raise HTTPException(status_code=400, detail="Module must contain config.yaml")

    try:
        async with aiofiles.open(config_path, "rb") as stream:
            config = yaml.safe_load(await stream.read())
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing config.yaml: {e}")
    except Exception:
        raise HTTPException(status_code=500, detail="Error reading config.yaml")

    return config


def load_config_yaml_sync(config_path: Path) -> Dict:
    """Load and parse config.yaml file synchronously."""
    if not config_path.exists():
        raise HTTPException(status_code=400, detail="Module must contain config.yaml")

    try:
        with open(config_path) as stream:
            config = yaml.safe_load(stream)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing config.yaml: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading config.yaml: {e}")

    return config


def validate_config_structure(config: Dict) -> None:
    """Validate the structure of the configuration."""
    if not isinstance(config, dict):
        raise HTTPException(
            status_code=400,
            detail="config.yaml must contain a valid configuration object",
        )

    required_fields = ["name", "version", "start"]
    missing_fields = [field for field in required_fields if field not in config]
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields in config.yaml: {', '.join(missing_fields)}",
        )


def process_binaries_field(binaries_raw) -> Dict:
    """Process and validate the binaries field from config."""
    if binaries_raw is None:
        return {}

    if isinstance(binaries_raw, str):
        try:
            return json.loads(binaries_raw) if binaries_raw else {}
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid JSON in binaries field"
            )
    elif isinstance(binaries_raw, dict):
        return binaries_raw
    else:
        return {}


def create_module_from_config(config: Dict) -> Module:
    """Create a Module instance from configuration data."""
    validate_config_structure(config)
    binaries = process_binaries_field(config.get("binaries"))

    try:
        return Module(
            name=convert_to_snake_case(config["name"]),
            description=config.get("description"),
            version=config["version"],
            start=config["start"],
            binaries=binaries,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error creating module object: {e}"
        )


async def get_module_by_name(db: AsyncSession, module_name: str) -> Optional[Module]:
    """Get a module by name from the database."""
    result = await db.execute(select(Module).where(Module.name == module_name))
    return result.scalar_one_or_none()


async def get_client_by_username(
    db: AsyncSession, client_username: str
) -> Optional[Client]:
    """Get a client by username from the database."""
    result = await db.execute(select(Client).where(Client.username == client_username))
    return result.scalar_one_or_none()


async def validate_module_and_client(
    db: AsyncSession, module_name: str, client_username: str
) -> Tuple[Module, Client]:
    """Validate that both module and client exist and return them."""
    module = await get_module_by_name(db, module_name)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    client = await get_client_by_username(db, client_username)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if not client.alive:
        raise HTTPException(status_code=400, detail="Client is not alive")

    return module, client


async def check_module_exists(db: AsyncSession, module_name: str) -> bool:
    """Check if a module exists in the database."""
    module = await get_module_by_name(db, module_name)
    return module is not None


def cleanup_module_directory(module_dir: Path) -> None:
    """Clean up module directory on error."""
    if module_dir and module_dir.exists():
        shutil.rmtree(module_dir, ignore_errors=True)


def create_backup_and_cleanup(module_path: Path) -> Optional[Path]:
    """Create backup of existing module and return backup path."""
    if not module_path.exists():
        return None

    backup_path = Path(str(module_path) + ".backup")
    if backup_path.exists():
        shutil.rmtree(backup_path)
    shutil.move(module_path, backup_path)
    return backup_path


def restore_from_backup(backup_path: Path, module_path: Path) -> None:
    """Restore module from backup."""
    if backup_path and backup_path.exists():
        if module_path.exists():
            shutil.rmtree(module_path, ignore_errors=True)
        shutil.move(backup_path, module_path)

import json
import os
import shutil
from pathlib import Path

import aiofiles
import yaml
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models.client import Client
from app.models.client_module import ClientModule
from app.models.module import Module
from app.schemas.general import BasicTaskResponse
from app.schemas.user_modules import UserModuleAllResponse, ModuleBasicInfo, ModuleInfo, ModuleAddRequest, \
    ModuleDirectoryContents, InstalledModuleInfo
from app.services.authentication import verify_access_token
from app.services.client_websockets import client_websocket_manager
from app.settings import settings
from app.utils import convert_to_snake_case, hyphen_to_snake_case, resolve_root

router = APIRouter(prefix="/user/modules")


@router.get("/all", response_model=UserModuleAllResponse)
async def user_modules_all(db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)):
    result = await db.execute(select(Module))
    modules = result.scalars().all()

    module_list = [
        ModuleBasicInfo(
            name=module.name,
            description=module.description,
            version=module.version,
            binaries_platform=list(module.binaries.keys()) if module.binaries else []
        ) for module in modules
    ]
    return UserModuleAllResponse(modules=module_list)


@router.post("/add", response_model=BasicTaskResponse)
async def user_modules_add(request: ModuleAddRequest, db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)):
    # Try relative paths first
    relative_module_path = Path(resolve_root("[ROOT]")) / "modules" / request.module_path

    if not os.path.exists(request.module_path):
        if not os.path.exists(relative_module_path):
            raise HTTPException(status_code=400, detail="Module path does not exist")

        else:
            module_path = relative_module_path
    else:
        module_path = request.module_path

    config_path = Path(module_path) / "config.yaml"
    if not os.path.isfile(config_path):
        raise HTTPException(status_code=400, detail="Module config.yaml does not exist")

    try:
        with open(config_path) as stream:
            config = yaml.safe_load(stream)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing config.yaml: {e}")
    except Exception:
        raise HTTPException(status_code=500, detail=f"Error reading config.yaml")

    binaries = config.get("binaries")
    if isinstance(binaries, str):
        binaries = json.loads(binaries) if binaries else {}
    elif binaries is None:
        binaries = {}
    # If binaries is already a dict, use it as-is

    try:
        module_info = ModuleInfo(
            name=config["name"],
            description=config.get("description"),
            version=config["version"],
            start=config["start"],
            binaries=binaries
        )
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required key in config.yaml: {e}")

    try:
        new_module = Module(
            name=convert_to_snake_case(module_info.name),
            description=module_info.description,
            version=module_info.version,
            start=module_info.start,
            binaries=binaries
        )
        db.add(new_module)
        await db.commit()
        await db.refresh(new_module)

        return {"result": "success"}

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add module to the database")


@router.post("/upload")
async def user_modules_upload(
        files: list[UploadFile] = File(...),
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_access_token),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    saved = []
    dest_path = None
    module_dir = None

    try:
        for f in files:
            if not f.filename:
                raise HTTPException(
                    status_code=400,
                    detail="File must have a filename"
                )

            rel_path = Path(f.filename)

            # Check for path traversal attempts - allow hidden files but block traversal
            if any(part in ['..', '.', ''] for part in rel_path.parts):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path - no relative path traversal allowed"
                )

            try:
                # Resolve path safely
                dest_path = (Path(settings.module_path) / rel_path).resolve()

                # Ensure the resolved path is still within module_path
                if not str(dest_path).startswith(str(Path(settings.module_path).resolve())):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid file path - outside allowed directory"
                    )
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Unsafe file path"
                )

            # Keep track of the module directory (parent of all files)
            if module_dir is None:
                module_dir = dest_path.parent
            elif dest_path.parent != module_dir and not str(dest_path).startswith(str(module_dir)):
                # Allow subdirectories within the same module
                potential_module_dir = dest_path
                while potential_module_dir.parent != Path(settings.module_path):
                    potential_module_dir = potential_module_dir.parent
                if module_dir != potential_module_dir:
                    module_dir = potential_module_dir

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(dest_path, "wb") as out:
                while True:
                    chunk = await f.read(1024)
                    if not chunk:
                        break
                    await out.write(chunk)

            saved.append(str(dest_path.relative_to(settings.module_path)))

        # Check for config.yaml in the module directory
        if module_dir is None:
            raise HTTPException(
                status_code=400,
                detail="No files were processed"
            )

        config_path = module_dir / "config.yaml"
        if not config_path.exists():
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail="Extracted module must contain config.yaml"
            )

        try:
            with open(config_path) as stream:
                config = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail=f"Error parsing config.yaml: {e}"
            )
        except Exception as e:
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail=f"Error reading config.yaml: {e}"
            )

        if not isinstance(config, dict):
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail="config.yaml must contain a valid configuration object"
            )

        # Parse binaries field safely
        binaries = config.get("binaries", {})
        if isinstance(binaries, str):
            try:
                binaries = json.loads(binaries) if binaries else {}
            except json.JSONDecodeError:
                shutil.rmtree(module_dir, ignore_errors=True)
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON in binaries field"
                )
        elif not isinstance(binaries, dict):
            binaries = {}

        # Validate required fields
        required_fields = ["name", "version", "start"]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields in config.yaml: {', '.join(missing_fields)}"
            )

        try:
            new_module = Module(
                name=convert_to_snake_case(config["name"]),
                description=config.get("description"),
                version=config["version"],
                start=config["start"],
                binaries=binaries
            )
        except Exception as e:
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail=f"Error creating module object: {e}"
            )

        try:
            # Check if module already exists
            result = await db.execute(
                select(Module).where(Module.name == new_module.name)
            )
            existing = result.scalar_one_or_none()
            if existing:
                shutil.rmtree(module_dir, ignore_errors=True)
                raise HTTPException(
                    status_code=409,
                    detail="Module already exists"
                )

            db.add(new_module)
            await db.commit()

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            await db.rollback()
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to add module to the database"
            )

        return {"result": "success", "files_saved": saved}

    except HTTPException:
        # Clean up on HTTP exceptions
        if module_dir and module_dir.exists():
            shutil.rmtree(module_dir, ignore_errors=True)
        raise
    except Exception as e:
        # Clean up on unexpected exceptions
        if module_dir and module_dir.exists():
            shutil.rmtree(module_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process module upload"
        )


@router.get("/get/{module_name}")
async def user_modules_get(
        module_name: str,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_access_token)
):
    module_name = hyphen_to_snake_case(module_name)
    result = await db.execute(select(Module).where(Module.name == module_name))
    module = result.scalar_one_or_none()

    if not module:
        raise HTTPException(
            status_code=404,
            detail="Module not found"
        )

    return {
        "name": module.name,
        "description": module.description,
        "version": module.version,
        "binaries": module.binaries
    }


@router.put("/update/{module_name}", response_model=BasicTaskResponse)
async def user_modules_update(
        module_name: str,
        files: list[UploadFile] = File(...),
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_access_token)
):
    module_name = hyphen_to_snake_case(module_name)
    result = await db.execute(select(Module).where(Module.name == module_name))
    existing_module = result.scalar_one_or_none()

    if not existing_module:
        raise HTTPException(
            status_code=404,
            detail="Module not found"
        )

    backup_path = None
    module_dir = None
    saved = []

    # Path where the module currently lives
    if settings.module_path:
        module_path = Path(settings.module_path) / existing_module.name
    else:
        mod_dir = Path(__file__).resolve().parent.parent / "modules"
        module_path = mod_dir / existing_module.name

    # Backup old module
    if module_path.exists():
        backup_path = Path(str(module_path) + ".backup")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.move(module_path, backup_path)

    try:
        # Save new uploaded directory structure
        for f in files:
            if not f.filename:
                raise HTTPException(
                    status_code=400,
                    detail="File must have a filename"
                )

            rel_path = Path(f.filename)

            # Prevent traversal
            if any(part in ['..', '.', ''] for part in rel_path.parts):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path - no relative path traversal allowed"
                )

            dest_path = (Path(settings.module_path) / rel_path).resolve()
            if not str(dest_path).startswith(str(Path(settings.module_path).resolve())):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path - outside allowed directory"
                )

            if module_dir is None:
                module_dir = dest_path.parent
            elif dest_path.parent != module_dir and not str(dest_path).startswith(str(module_dir)):
                potential_module_dir = dest_path
                while potential_module_dir.parent != Path(settings.module_path):
                    potential_module_dir = potential_module_dir.parent
                if module_dir != potential_module_dir:
                    module_dir = potential_module_dir

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(dest_path, "wb") as out:
                while True:
                    chunk = await f.read(1024)
                    if not chunk:
                        break
                    await out.write(chunk)

            saved.append(str(dest_path.relative_to(settings.module_path)))

        if module_dir is None:
            raise HTTPException(
                status_code=400,
                detail="No files were processed"
            )

        config_path = module_dir / "config.yaml"
        if not config_path.exists():
            raise HTTPException(
                status_code=400,
                detail="Updated module must contain config.yaml"
            )

        try:
            with open(config_path) as stream:
                config = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error parsing config.yaml: {e}"
            )

        required_fields = ["name", "version", "start"]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields in config.yaml: {', '.join(missing_fields)}"
            )

        binaries = config.get("binaries", {})
        if isinstance(binaries, str):
            try:
                binaries = json.loads(binaries) if binaries else {}
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON in binaries field"
                )
        elif not isinstance(binaries, dict):
            binaries = {}

        # Update DB entry
        new_module_name = convert_to_snake_case(config["name"])
        existing_module.name = new_module_name
        existing_module.description = config.get("description")
        existing_module.version = config["version"]
        existing_module.start = config["start"]
        existing_module.binaries = binaries

        await db.commit()

        # If module name changed, rename directory
        if new_module_name != module_name:
            new_module_path = Path(settings.module_path) / new_module_name
            if new_module_path.exists():
                shutil.rmtree(new_module_path, ignore_errors=True)
            shutil.move(module_dir, new_module_path)

        if backup_path and backup_path.exists():
            shutil.rmtree(backup_path)

        return {"result": "success"}

    except HTTPException:
        if backup_path and backup_path.exists():
            if module_path.exists():
                shutil.rmtree(module_path, ignore_errors=True)
            shutil.move(backup_path, module_path)
        raise
    except Exception as e:
        await db.rollback()
        if backup_path and backup_path.exists():
            if module_path.exists():
                shutil.rmtree(module_path, ignore_errors=True)
            shutil.move(backup_path, module_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update module: {e}"
        )


@router.delete("/delete/{module_name}", response_model=BasicTaskResponse)
async def user_modules_delete(
        module_name: str,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_access_token)
):
    module_name = hyphen_to_snake_case(module_name)
    result = await db.execute(select(Module).where(Module.name == module_name))
    module = result.scalar_one_or_none()

    if not module:
        raise HTTPException(
            status_code=404,
            detail="Module not found"
        )

    try:
        # Remove from database
        await db.delete(module)
        await db.commit()

        # Remove module directory if it exists
        if settings.module_path and os.path.isdir(settings.module_path):
            module_path = Path(settings.module_path) / module_name
        else:
            mod_dir = Path(__file__).resolve().parent.parent / "modules"
            module_path = mod_dir / module_name

        if os.path.exists(module_path):
            shutil.rmtree(module_path)

        return {"result": "success"}

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete module"
        )


@router.get("/query-module-dir", response_model=ModuleDirectoryContents)
async def user_modules_query_module_dir():
    contents_list = []
    if settings.module_path and os.path.isdir(settings.module_path):
        try:
            for item in os.listdir(settings.module_path):
                item_path = os.path.join(settings.module_path, item)
                if os.path.isfile(item_path):
                    contents_list.append({"file": item})
                elif os.path.isdir(item_path):
                    contents_list.append({"directory": item})
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to query module directory: {str(e)}"
            )
    else:
        return {"contents": []}

    return {"contents": contents_list}


@router.get("/installed/{client_username}")
async def user_modules_installed_client_username(
        client_username: str,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_access_token)
):
    client = await db.execute(
        select(Client)
        .options(selectinload(Client.client_modules).selectinload(ClientModule.module))
        .where(Client.username == client_username)
    )
    client = client.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=400,
            detail="Client username not found"
        )

    mod_names = []
    for client_mod in client.client_modules:
        mod_info = InstalledModuleInfo(
            name=client_mod.module.name,
            description=client_mod.module.description,
            version=client_mod.module.version,
            status=client_mod.status
        )
        mod_names.append(mod_info)

    return mod_names


@router.post("/set-installed/{client_username}")
async def user_modules_set_installed_client_username(
        client_username: str,
        module_name: str,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_access_token)
):
    client = await db.execute(
        select(Client)
        .options(selectinload(Client.client_modules).selectinload(ClientModule.module))
        .where(Client.username == client_username)
    )
    client = client.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=400,
            detail="Client username not found"
        )

    module = await db.execute(select(Module).where(Module.name == module_name))
    module = module.scalar_one_or_none()

    if not module:
        raise HTTPException(
            status_code=400,
            detail="Module not found"
        )

    for client_mod in client.client_modules:
        if client_mod.module.name == module.name:
            raise HTTPException(
                status_code=409,
                detail="Module already installed on client"
            )

    client_module = ClientModule(
        client_name=client.username,
        module_name=module.name,
        status="installed"
    )

    client.client_modules.append(client_module)
    db.add(client_module)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to add installed module to the database"
        )

    return {"result": "success"}


@router.get("/run/{module_name}")
async def user_modules_run_module_name(
        module_name: str,
        client_username: str,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_access_token)
):
    module = await db.execute(select(Module).where(Module.name == module_name))
    module = module.scalar_one_or_none()
    if not module:
        raise HTTPException(
            status_code=404,
            detail="Module not found"
        )

    client = await db.execute(select(Client).where(Client.username == client_username))
    client = client.scalar_one_or_none()
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not found"
        )

    if not client.alive:
        raise HTTPException(
            status_code=400,
            detail="Client is not alive"
        )

    client_module = await db.execute(select(ClientModule).where(ClientModule.client_name == client_username and ClientModule.module_name == module.name))
    client_module = client_module.scalar_one_or_none()
    if not client_module:
        raise HTTPException(
            status_code=400,
            detail="Module not installed on client"
        )

    await client_websocket_manager.send_to_client(
        client_uuid=str(client.uuid),
        message={
            "message_type": "module_run",
            "module_name": module.name
        }
    )

    return {"result": "success"}

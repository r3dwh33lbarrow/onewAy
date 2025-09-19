import json
import os
import shutil
from pathlib import Path

import aiofiles
import yaml
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models.client import Client
from app.models.client_module import ClientModule
from app.models.module import Module
from app.schemas.general import BasicTaskResponse
from app.schemas.module import *
from app.services.authentication import verify_access_token, get_current_user
from app.services.client_websockets import client_websocket_manager
from app.settings import settings
from app.utils import convert_to_snake_case, hyphen_to_snake_case

router = APIRouter(prefix="/module")


@router.get("/all", response_model=UserModuleAllResponse)
async def module_all(
    db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)
):
    result = await db.execute(select(Module))
    modules = result.scalars().all()

    module_list = [
        ModuleBasicInfo(
            name=module.name,
            description=module.description,
            version=module.version,
            start=module.start,
            binaries_platform=list(module.binaries.keys()) if module.binaries else [],
        )
        for module in modules
    ]
    return UserModuleAllResponse(modules=module_list)


@router.put("/add", response_model=BasicTaskResponse)
async def module_add(
    request: ModuleAddRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    relative_module_path = Path(settings.paths.module_dir) / request.module_path

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
        async with aiofiles.open(config_path, "rb") as stream:
            config = yaml.safe_load(await stream.read())
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing config.yaml: {e}")
    except Exception:
        raise HTTPException(status_code=500, detail=f"Error reading config.yaml")

    binaries = config.get("binaries")
    if binaries:
        binaries = json.loads(binaries)
    else:
        binaries = {}

    try:
        module_info = ModuleInfo(
            name=config["name"],
            description=config.get("description"),
            version=config["version"],
            start=config["start"],
            binaries=binaries,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=400, detail=f"Missing required key in config.yaml: {e}"
        )

    try:
        new_module = Module(
            name=convert_to_snake_case(module_info.name),
            description=module_info.description,
            version=module_info.version,
            start=module_info.start,
            binaries=binaries,
        )
        db.add(new_module)
        await db.commit()
        await db.refresh(new_module)

        return {"result": "success"}

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to add module to the database"
        )


@router.put("/upload")
async def module_upload(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    saved = []
    module_dir = None

    try:
        for f in files:
            if not f.filename:
                raise HTTPException(status_code=400, detail="File must have a filename")

            rel_path = Path(f.filename)

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
            except Exception:
                raise HTTPException(status_code=400, detail="Unsafe file path")

            if module_dir is None:
                module_dir = dest_path.parent
            elif dest_path.parent != module_dir and not str(dest_path).startswith(
                str(module_dir)
            ):
                potential_module_dir = dest_path
                while potential_module_dir.parent != Path(settings.paths.module_dir):
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

            saved.append(str(dest_path.relative_to(settings.paths.module_dir)))

        if module_dir is None:
            raise HTTPException(status_code=400, detail="No files were processed")

        config_path = module_dir / "config.yaml"
        if not config_path.exists():
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400, detail="Extracted module must contain config.yaml"
            )

        try:
            with open(config_path) as stream:
                config = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400, detail=f"Error parsing config.yaml: {e}"
            )
        except Exception as e:
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400, detail=f"Error reading config.yaml: {e}"
            )

        if not isinstance(config, dict):
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail="config.yaml must contain a valid configuration object",
            )

        binaries = config.get("binaries", {})
        if isinstance(binaries, str):
            try:
                binaries = json.loads(binaries) if binaries else {}
            except json.JSONDecodeError:
                shutil.rmtree(module_dir, ignore_errors=True)
                raise HTTPException(
                    status_code=400, detail="Invalid JSON in binaries field"
                )
        elif not isinstance(binaries, dict):
            binaries = {}

        required_fields = ["name", "version", "start"]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields in config.yaml: {', '.join(missing_fields)}",
            )

        try:
            new_module = Module(
                name=convert_to_snake_case(config["name"]),
                description=config.get("description"),
                version=config["version"],
                start=config["start"],
                binaries=binaries,
            )
        except Exception as e:
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400, detail=f"Error creating module object: {e}"
            )

        try:
            result = await db.execute(
                select(Module).where(Module.name == new_module.name)
            )
            existing = result.scalar_one_or_none()
            if existing:
                shutil.rmtree(module_dir, ignore_errors=True)
                raise HTTPException(status_code=409, detail="Module already exists")

            db.add(new_module)
            await db.commit()

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            shutil.rmtree(module_dir, ignore_errors=True)
            raise HTTPException(
                status_code=500, detail="Failed to add module to the database"
            )

        return {"result": "success", "files_saved": saved}

    except HTTPException:
        if module_dir and module_dir.exists():
            shutil.rmtree(module_dir, ignore_errors=True)
        raise
    except Exception as e:
        if module_dir and module_dir.exists():
            shutil.rmtree(module_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Failed to process module upload")


@router.get("/get/{module_name}")
async def module_get(
    module_name: str, db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)
):
    module_name = hyphen_to_snake_case(module_name)
    result = await db.execute(select(Module).where(Module.name == module_name))
    module = result.scalar_one_or_none()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    return {
        "name": module.name,
        "description": module.description,
        "version": module.version,
        "binaries": module.binaries,
    }


@router.put("/update/{module_name}", response_model=BasicTaskResponse)
async def module_update(
    module_name: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    module_name = hyphen_to_snake_case(module_name)
    result = await db.execute(select(Module).where(Module.name == module_name))
    existing_module = result.scalar_one_or_none()

    if not existing_module:
        raise HTTPException(status_code=404, detail="Module not found")

    backup_path = None
    module_dir = None
    saved = []

    module_path = settings.paths.module_dir

    if module_path.exists():
        backup_path = Path(str(module_path) + ".backup")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.move(module_path, backup_path)

    try:
        for f in files:
            if not f.filename:
                raise HTTPException(status_code=400, detail="File must have a filename")

            rel_path = Path(f.filename)

            if any(part in ["..", ".", ""] for part in rel_path.parts):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path - no relative path traversal allowed",
                )

            dest_path = (Path(settings.paths.module_dir) / rel_path).resolve()
            if not str(dest_path).startswith(str(Path(settings.paths.module_dir).resolve())):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path - outside allowed directory",
                )

            if module_dir is None:
                module_dir = dest_path.parent
            elif dest_path.parent != module_dir and not str(dest_path).startswith(
                str(module_dir)
            ):
                potential_module_dir = dest_path
                while potential_module_dir.parent != Path(settings.paths.module_dir):
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

            saved.append(str(dest_path.relative_to(settings.paths.module_dir)))

        if module_dir is None:
            raise HTTPException(status_code=400, detail="No files were processed")

        config_path = module_dir / "config.yaml"
        if not config_path.exists():
            raise HTTPException(
                status_code=400, detail="Updated module must contain config.yaml"
            )

        try:
            with open(config_path) as stream:
                config = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=400, detail=f"Error parsing config.yaml: {e}"
            )

        required_fields = ["name", "version", "start"]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields in config.yaml: {', '.join(missing_fields)}",
            )

        binaries = config.get("binaries", {})
        if isinstance(binaries, str):
            try:
                binaries = json.loads(binaries) if binaries else {}
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400, detail="Invalid JSON in binaries field"
                )
        elif not isinstance(binaries, dict):
            binaries = {}

        new_module_name = convert_to_snake_case(config["name"])
        existing_module.name = new_module_name
        existing_module.description = config.get("description")
        existing_module.version = config["version"]
        existing_module.start = config["start"]
        existing_module.binaries = binaries

        await db.commit()

        if new_module_name != module_name:
            new_module_path = Path(settings.paths.module_dir) / new_module_name
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
        raise HTTPException(status_code=500, detail=f"Failed to update module: {e}")


@router.delete("/delete/{module_name}", response_model=BasicTaskResponse)
async def module_delete(
    module_name: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)
):
    module_name = hyphen_to_snake_case(module_name)
    result = await db.execute(select(Module).where(Module.name == module_name))
    module = result.scalar_one_or_none()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    try:
        await db.delete(module)
        await db.commit()

        module_path = Path(settings.paths.module_dir) / module_name

        if os.path.exists(module_path):
            shutil.rmtree(module_path)

        return {"result": "success"}

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete module")


@router.get("/query-module-dir", response_model=ModuleDirectoryContents)
async def module_query_module_dir(_=Depends(get_current_user)):
    contents_list = []
    try:
        for item in os.listdir(settings.paths.module_dir):
            item_path = os.path.join(settings.paths.module_dir, item)
            if os.path.isfile(item_path):
                contents_list.append({"file": item})
            elif os.path.isdir(item_path):
                contents_list.append({"directory": item})
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to query module directory: {str(e)}"
        )

    return {"contents": contents_list}


@router.get("/installed/{client_username}")
async def module_installed_client_username(
    client_username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_access_token),
):
    client = await db.execute(
        select(Client)
        .options(selectinload(Client.client_modules).selectinload(ClientModule.module))
        .where(Client.username == client_username)
    )
    client = client.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=400, detail="Client username not found")

    mod_names = []
    for client_mod in client.client_modules:
        mod_info = InstalledModuleInfo(
            name=client_mod.module.name,
            description=client_mod.module.description,
            version=client_mod.module.version,
            status=client_mod.status,
        )
        mod_names.append(mod_info)

    return mod_names


@router.post("/set-installed/{client_username}")
async def module_set_installed_client_username(
    client_username: str,
    module_name: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_access_token),
):
    client = await db.execute(
        select(Client)
        .options(selectinload(Client.client_modules).selectinload(ClientModule.module))
        .where(Client.username == client_username)
    )
    client = client.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=400, detail="Client username not found")

    module = await db.execute(select(Module).where(Module.name == module_name))
    module = module.scalar_one_or_none()

    if not module:
        raise HTTPException(status_code=400, detail="Module not found")

    for client_mod in client.client_modules:
        if client_mod.module.name == module.name:
            raise HTTPException(
                status_code=409, detail="Module already installed on client"
            )

    client_module = ClientModule(
        client_name=client.username, module_name=module.name, status="installed"
    )

    client.client_modules.append(client_module)
    db.add(client_module)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to add installed module to the database"
        )

    return {"result": "success"}


@router.get("/run/{module_name}")
async def module_run_module_name(
    module_name: str,
    client_username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    module = await db.execute(select(Module).where(Module.name == module_name))
    module = module.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    client = await db.execute(select(Client).where(Client.username == client_username))
    client = client.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if not client.alive:
        raise HTTPException(status_code=400, detail="Client is not alive")

    client_module = await db.execute(
        select(ClientModule).where(
            (ClientModule.client_name == client_username)
            & (ClientModule.module_name == module.name)
        )
    )
    client_module = client_module.scalar_one_or_none()
    if not client_module:
        raise HTTPException(status_code=400, detail="Module not installed on client")

    if (module.start or "").lower() != "manual":
        raise HTTPException(
            status_code=400, detail="Module is not configured for manual start"
        )

    await client_websocket_manager.send_to_client(
        client_uuid=str(client.uuid),
        message={"message_type": "module_run", "module_name": module.name},
    )

    return {"result": "success"}


@router.get("/cancel/{module_name}")
async def module_cancel_module_name(
    module_name: str,
    client_username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    module = await db.execute(select(Module).where(Module.name == module_name))
    module = module.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    client = await db.execute(select(Client).where(Client.username == client_username))
    client = client.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if not client.alive:
        raise HTTPException(status_code=400, detail="Client is not alive")

    await client_websocket_manager.send_to_client(
        client_uuid=str(client.uuid),
        message={"message_type": "module_cancel", "module_name": module.name},
    )

    return {"result": "success"}

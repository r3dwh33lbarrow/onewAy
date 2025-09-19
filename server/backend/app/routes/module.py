import os
import shutil
from pathlib import Path
from typing import Iterable

import aiofiles
import yaml
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
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


def _modules_root() -> Path:
    return Path(settings.paths.module_dir)


def _resolve_module_path(path_str: str) -> Path:
    direct = Path(path_str)
    if direct.exists():
        return direct
    relative = _modules_root() / path_str
    if relative.exists():
        return relative
    raise HTTPException(status_code=400, detail="Module path does not exist")


def _require_config_yaml(module_dir: Path) -> Path:
    config_path = module_dir / "config.yaml"
    if not config_path.is_file():
        raise HTTPException(status_code=400, detail="Module config.yaml does not exist")
    return config_path


def _read_yaml(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as stream:
            return yaml.safe_load(stream) or {}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing config.yaml: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error reading config.yaml") from e


def _normalize_module_name_from_fs(path: Path) -> str:
    return convert_to_snake_case(hyphen_to_snake_case(path.name))


async def _get_module_or_404(db: AsyncSession, module_name: str) -> Module:
    result = await db.execute(select(Module).where(Module.name == module_name))
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module


async def _get_client_or_404(db: AsyncSession, username: str) -> Client:
    result = await db.execute(select(Client).where(Client.username == username))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _ensure_client_alive(client: Client) -> None:
    if not client.alive:
        raise HTTPException(status_code=400, detail="Client is not alive")


async def _write_upload_files_to_dir(files: Iterable[UploadFile], target_dir: Path) -> list[str]:
    saved: list[str] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        if not f.filename:
            raise HTTPException(status_code=400, detail="File must have a filename")
        rel_path = Path(f.filename.strip("/").strip("\\"))
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise HTTPException(status_code=400, detail=f"Invalid filename: {f.filename}")
        dest_path = target_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with aiofiles.open(dest_path, "wb") as out:
                content = await f.read()
                await out.write(content)
        finally:
            await f.close()
        saved.append(str(rel_path))
    return saved


@router.get("/all", response_model=UserModuleAllResponse)
async def module_all(
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_access_token),
):
    result = await db.execute(select(Module))
    modules = result.scalars().all()
    return {
        "modules": [
            ModuleBasicInfo(
                name=m.name,
                description=m.description,
                version=m.version,
                start=m.start,
                binaries_platform=(list((m.binaries or {}).keys()) if isinstance(m.binaries, dict) else list(m.binaries or [])),
            )
            for m in modules
        ]
    }


@router.put("/add", response_model=BasicTaskResponse)
async def module_add(
    request: ModuleAddRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    module_path = _resolve_module_path(request.module_path)
    config_path = _require_config_yaml(module_path)
    config = _read_yaml(config_path)
    name = convert_to_snake_case(
        hyphen_to_snake_case(
            request.module_name or _normalize_module_name_from_fs(module_path)
        )
    )
    description = config.get("description") or request.description or ""
    version = str(config.get("version") or request.version or "0.0.1")
    start = config.get("start") or request.start or ""
    binaries = config.get("binaries") or {}
    new_module = Module(
        name=name,
        description=description,
        version=version,
        start=start,
        binaries=binaries,
    )
    db.add(new_module)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Module already exists") from e
    return {"result": "success"}


@router.put("/upload")
async def module_upload(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    first = files[0].filename or ""
    top_dir = Path(first).parts[0] if "/" in first or "\\" in first else Path(first).stem
    if not top_dir:
        raise HTTPException(status_code=400, detail="Uploaded files must be inside a directory")
    module_dir = _modules_root() / convert_to_snake_case(hyphen_to_snake_case(top_dir))
    if module_dir.exists():
        shutil.rmtree(module_dir, ignore_errors=True)
    try:
        files_saved = await _write_upload_files_to_dir(files, module_dir)
        config_path = _require_config_yaml(module_dir)
        config = _read_yaml(config_path)
        name = convert_to_snake_case(
            hyphen_to_snake_case(config.get("name") or module_dir.name)
        )
        description = config.get("description") or ""
        version = str(config.get("version") or "0.0.1")
        start = config.get("start") or ""
        binaries = config.get("binaries") or {}
        existing_q = await db.execute(select(Module).where(Module.name == name))
        existing = existing_q.scalar_one_or_none()
        if existing:
            existing.description = description
            existing.version = version
            existing.start = start
            existing.binaries = binaries
        else:
            db.add(
                Module(
                    name=name,
                    description=description,
                    version=version,
                    start=start,
                    binaries=binaries,
                )
            )
        await db.commit()
        return {"result": "success", "files_saved": files_saved}
    except HTTPException:
        if module_dir.exists():
            shutil.rmtree(module_dir, ignore_errors=True)
        raise
    except Exception:
        if module_dir.exists():
            shutil.rmtree(module_dir, ignore_errors=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process module upload")


@router.get("/get/{module_name}")
async def module_get(
    module_name: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_access_token),
):
    module = await _get_module_or_404(db, module_name)
    return ModuleInfo(
        name=module.name,
        description=module.description,
        version=module.version,
        start=module.start,
        binaries=module.binaries,
    )


@router.put("/update/{module_name}", response_model=BasicTaskResponse)
async def module_update(
    module_name: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    module = await _get_module_or_404(db, module_name)
    module_dir = _modules_root() / module.name
    tmp_dir = module_dir.with_name(module_dir.name + "_tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        await _write_upload_files_to_dir(files, tmp_dir)
        config_path = _require_config_yaml(tmp_dir)
        config = _read_yaml(config_path)
        if module_dir.exists():
            shutil.rmtree(module_dir, ignore_errors=True)
        tmp_dir.rename(module_dir)
        module.description = config.get("description") or module.description
        module.version = str(config.get("version") or module.version)
        module.start = config.get("start") or module.start
        module.binaries = config.get("binaries") or module.binaries
        await db.commit()
        return {"result": "success"}
    except HTTPException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update module")


@router.delete("/delete/{module_name}", response_model=BasicTaskResponse)
async def module_delete(
    module_name: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    module = await _get_module_or_404(db, module_name)
    module_dir = _modules_root() / module.name
    await db.execute(delete(ClientModule).where(ClientModule.module_name == module.name))
    await db.execute(delete(Module).where(Module.name == module.name))
    await db.commit()
    if module_dir.exists():
        shutil.rmtree(module_dir, ignore_errors=True)
    return {"result": "success"}


@router.get("/query-module-dir", response_model=ModuleDirectoryContents)
async def module_query_module_dir(_=Depends(get_current_user)):
    root = _modules_root()
    root.mkdir(parents=True, exist_ok=True)
    contents_list: list[dict[str, str]] = []
    for base, _, files in os.walk(root):
        base_path = Path(base)
        for f in files:
            rel = (base_path / f).relative_to(root)
            contents_list.append({"path": str(rel)})
    return {"contents": contents_list}


@router.get("/installed/{client_username}")
async def module_installed_client_username(
    client_username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(
        select(ClientModule)
        .options(selectinload(ClientModule.module))
        .join(Client, Client.username == ClientModule.client_name)
        .where(Client.username == client_username)
    )
    client_modules = result.scalars().all()
    items = []
    for cm in client_modules:
        mod = cm.module
        status = getattr(cm, "status", None)
        if status is None:
            if getattr(cm, "running", False):
                status = "running"
            elif getattr(cm, "installed", False):
                status = "installed"
        items.append(
            InstalledModuleInfo(
                name=mod.name,
                description=mod.description,
                version=mod.version,
                status=status,
            )
        )
    return {"modules": items}


@router.post("/set-installed/{client_username}")
async def module_set_installed_client_username(
    client_username: str,
    request: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    client = await _get_client_or_404(db, client_username)
    incoming: list[dict] = list(request.get("modules") or [])
    desired: dict[str, str | None] = {}
    for m in incoming:
        if "name" not in m:
            continue
        norm_name = convert_to_snake_case(hyphen_to_snake_case(m["name"]))
        status = m.get("status")
        if status is None:
            installed = bool(m.get("installed"))
            running = bool(m.get("running"))
            status = "running" if running else ("installed" if installed else None)
        desired[norm_name] = status
    if not desired:
        return {"result": "success"}
    result = await db.execute(select(Module).where(Module.name.in_(list(desired.keys()))))
    modules_by_name = {m.name: m for m in result.scalars().all()}
    for name, status in desired.items():
        mod = modules_by_name.get(name)
        if not mod:
            continue
        existing_q = await db.execute(
            select(ClientModule).where(
                ClientModule.client_name == client.username, ClientModule.module_name == mod.name
            )
        )
        cm = existing_q.scalar_one_or_none()
        if cm:
            cm.status = status
        else:
            db.add(
                ClientModule(
                    client_name=client.username,
                    module_name=mod.name,
                    status=status,
                )
            )
    await db.commit()
    return {"result": "success"}


@router.get("/run/{module_name}")
async def module_run_module_name(
    module_name: str,
    client_username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    module = await _get_module_or_404(db, module_name)
    client = await _get_client_or_404(db, client_username)
    _ensure_client_alive(client)
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
    module = await _get_module_or_404(db, module_name)
    client = await _get_client_or_404(db, client_username)
    _ensure_client_alive(client)
    await client_websocket_manager.send_to_client(
        client_uuid=str(client.uuid),
        message={"message_type": "module_cancel", "module_name": module.name},
    )
    return {"result": "success"}

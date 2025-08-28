import hashlib
import io
import os
import shutil
import zipfile
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import RedirectResponse

from app.dependencies import get_db
from app.models.module import Module
from app.schemas.general import BasicTaskResponse
from app.schemas.user_modules import UserModuleAllResponse, ModuleBasicInfo, ModuleInfo
from app.services.authentication import verify_access_token
from app.settings import settings
from app.utils import convert_to_snake_case, hyphen_to_snake_case

router = APIRouter(prefix="/user/modules")


@router.get("/all", response_model=UserModuleAllResponse)
async def user_modules_all(db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)):
    result = await db.execute(select(Module))
    modules = result.scalars().all()

    module_list = [
        ModuleBasicInfo(
            name=module.name,
            path=module.path,
            version=module.version
        ) for module in modules
    ]
    return UserModuleAllResponse(modules=module_list)


@router.post("/add", response_model=BasicTaskResponse)
async def user_modules_add(module_path: str, db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)):
    if not os.path.exists(module_path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module path does not exist")

    config_path = Path(module_path) / "config.yaml"
    if not os.path.isfile(config_path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module config.yaml does not exist")

    try:
        with open(config_path) as stream:
            config = yaml.safe_load(stream)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error parsing config.yaml: {e}")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error reading config.yaml")

    try:
        module_info = ModuleInfo(
            name=config["name"],
            description=config.get("description"),
            path=config["path"],
            version=config["version"]
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required key in config.yaml: {e}")

    try:
        new_module = Module(
            name=convert_to_snake_case(module_info.name),
            description=module_info.description,
            path=module_info.path,
            version=module_info.version
        )
        db.add(new_module)
        await db.commit()
        await db.refresh(new_module)

        return {"result": "success"}

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add module to the database")


@router.post("/upload")
async def user_modules_upload(dev_name: str, file: UploadFile = File(...), _=Depends(verify_access_token)):
    # Dev name means camelcase; add to docstrings
    if settings.module_path:
        module_path = Path(settings.module_path) / dev_name
    else:
        mod_dir = Path(__file__).resolve().parent.parent / "modules"
        module_path = mod_dir / dev_name
        if not os.path.exists(mod_dir):
            os.makedirs(mod_dir)

    try:
        os.mkdir(module_path)
    except FileExistsError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module directory already exists")

    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a ZIP archive"
        )

    try:
        content = await file.read()

        with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_ref:
            for member in zip_ref.namelist():
                if os.path.isabs(member) or ".." in member:
                    os.rmdir(module_path)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid file path in archive: {member}"
                    )

            zip_ref.extractall(module_path)

        config_path = module_path / "config.yaml"
        if not config_path.exists():
            shutil.rmtree(module_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extracted module must contain config.yaml"
            )

        return RedirectResponse(
            url=f"/modules/add?module_path={str(module_path)}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except zipfile.BadZipFile:
        if os.path.exists(module_path):
            os.rmdir(module_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ZIP file"
        )
    except Exception:
        if os.path.exists(module_path):
            shutil.rmtree(module_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract module"
        )


@router.put("/update/{module_name}", response_model=BasicTaskResponse)
async def user_modules_update(
        module_name: str,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_access_token)
):
    module_name = hyphen_to_snake_case(module_name)
    result = await db.execute(select(Module).where(Module.name == module_name))
    existing_module = result.scalar_one_or_none()

    if not existing_module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )

    if settings.module_path:
        module_path = Path(settings.module_path) / existing_module.name
    else:
        mod_dir = Path(__file__).resolve().parent.parent / "modules"
        module_path = mod_dir / existing_module.name

    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a ZIP archive"
        )

    backup_path = None
    if os.path.exists(module_path):
        backup_path = Path(str(module_path) + ".backup")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.move(module_path, backup_path)

    try:
        os.makedirs(module_path, exist_ok=True)

        content = await file.read()

        with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_ref:
            for member in zip_ref.namelist():
                if os.path.isabs(member) or ".." in member:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid file path in archive: {member}"
                    )

            zip_ref.extractall(module_path)

        config_path = module_path / "config.yaml"
        if not config_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extracted module must contain config.yaml"
            )

        try:
            with open(config_path) as stream:
                config = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error parsing config.yaml: {e}"
            )

        try:
            module_info = ModuleInfo(
                name=config["name"],
                description=config.get("description"),
                path=config["path"],
                version=config["version"]
            )
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required key in config.yaml: {e}"
            )

        existing_module.name = convert_to_snake_case(module_info.name)
        existing_module.description = module_info.description
        existing_module.path = module_info.path
        existing_module.version = module_info.version

        await db.commit()
        await db.refresh(existing_module)

        if backup_path and backup_path.exists():
            shutil.rmtree(backup_path)

        return {"result": "success"}

    except Exception as e:
        await db.rollback()

        if os.path.exists(module_path):
            shutil.rmtree(module_path)
        if backup_path and backup_path.exists():
            shutil.move(backup_path, module_path)

        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update module: {str(e)}"
            )


@router.delete("/delete/{module_name}")
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )

    if settings.module_path:
        module_path = Path(settings.module_path) / module.name
    else:
        mod_dir = Path(__file__).resolve().parent.parent / "modules"
        module_path = mod_dir / module.name

    try:
        await db.delete(module)
        await db.commit()

        if os.path.exists(module_path):
            shutil.rmtree(module_path)

        return {"result": "success", "message": f"Module '{module.name}' deleted successfully"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete module: {str(e)}"
        )


@router.get("/{module_name}", response_model=ModuleInfo)
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )

    return ModuleInfo(
        name=module.name,
        description=module.description,
        path=module.path,
        version=module.version
    )
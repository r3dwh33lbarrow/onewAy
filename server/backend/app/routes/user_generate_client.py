import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.client import Client
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.general import BasicTaskResponse
from app.schemas.user_generate_client import GenerateClientRequest
from app.services.authentication import get_current_user
from app.services.client_generation import (
    generate_client_binary,
    generate_client_config,
    move_modules,
)
from app.services.password import hash_password
from app.settings import settings

router = APIRouter(prefix="/user", tags=["User Client"])


def _safe_rmtree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except AttributeError:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


@router.get("/verify-rust", response_model=BasicTaskResponse)
async def user_verify_rust(_=Depends(get_current_user)):
    for command in (("rustc", "--version"), ("cargo", "--version")):
        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {"result": "failed"}

    return {"result": "success"}


@router.post("/generate-client")
async def user_generate_client(
    client_info: GenerateClientRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    path_name = f"{str(uuid.uuid4())}_{user.username}"
    prefix = Path(settings.paths.resources_dir) / "clients"
    prefix.mkdir(parents=True, exist_ok=True)

    full_path = prefix / path_name

    existing_client_result = await db.execute(
        select(Client).where(Client.username == client_info.username)
    )
    existing_client = existing_client_result.scalar_one_or_none()

    try:
        full_path.mkdir()
        generate_client_config(full_path, client_info.username, client_info.password)
        move_modules(full_path, client_info.platform, client_info.packaged_modules)
        generate_client_binary(
            full_path,
            client_info.platform,
            str(client_info.ip_address),
            client_info.port,
        )
        archive_path = shutil.make_archive(
            str(full_path), "zip", root_dir=prefix, base_dir=path_name
        )

        hashed_password_value = hash_password(client_info.password)

        if existing_client:
            existing_client.hashed_password = hashed_password_value
            existing_client.client_version = settings.app.client_version
            existing_client.revoked = False
            existing_client.alive = False
            existing_client.ip_address = None
            existing_client.last_contact = None
            existing_client.hostname = None

            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.client_uuid == existing_client.uuid)
                .values(revoked=True)
            )
        else:
            new_client = Client(
                username=client_info.username,
                hashed_password=hashed_password_value,
                client_version=settings.app.client_version,
            )
            db.add(new_client)
        await db.commit()
    except HTTPException:
        if full_path.exists():
            shutil.rmtree(full_path, ignore_errors=True)
        raise
    except Exception as error:
        if full_path.exists():
            shutil.rmtree(full_path, ignore_errors=True)

        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate client: {error}",
        ) from error

    background_tasks.add_task(_safe_rmtree, full_path)
    background_tasks.add_task(_safe_unlink, Path(archive_path))

    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=f"{path_name}.zip",
        background=background_tasks,
    )

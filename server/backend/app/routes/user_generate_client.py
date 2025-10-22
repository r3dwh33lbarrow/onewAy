import os
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User
from app.schemas.general import BasicTaskResponse
from app.schemas.user_generate_client import GenerateClientRequest
from app.services.authentication import get_current_user
from app.services.client_generation import (
    generate_client_binary,
    generate_client_config,
    move_modules,
)
from app.settings import settings

router = APIRouter(prefix="/user", tags=["User Client"])


@router.get("/verify-rust", response_model=BasicTaskResponse)
async def user_verify_rust(_=Depends(get_current_user)) -> BasicTaskResponse:
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


@router.post(
    "/generate-client",
    response_model=BasicTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def user_generate_client(
    client_info: GenerateClientRequest, user: User = Depends(get_current_user)
) -> BasicTaskResponse:
    path_name = f"{str(uuid.uuid4())}_{user.username}"
    prefix = Path(settings.paths.resources_dir) / "clients"
    prefix.mkdir(parents=True, exist_ok=True)

    full_path = prefix / path_name

    try:
        full_path.mkdir()
        generate_client_config(
            full_path, client_info.username, client_info.password
        )
        move_modules(full_path, client_info.packaged_modules)
        generate_client_binary(
            full_path,
            client_info.platform,
            str(client_info.ip_address),
            client_info.port,
        )
    except Exception as error:
        if full_path.exists():
            shutil.rmtree(full_path, ignore_errors=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate client: {error}",
        ) from error

    return {"result": "success"}

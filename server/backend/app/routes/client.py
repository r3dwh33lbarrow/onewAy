import os.path
import platform
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.client import Client
from app.schemas.client import (
    BasicClientInfo,
    ClientAllInfo,
    ClientAllResponse,
    ClientUpdateInfo,
)
from app.services import authentication
from app.services.authentication import get_current_client, get_current_user
from app.settings import settings

router = APIRouter(prefix="/client")


@router.get("/get/{username}", response_model=ClientAllInfo)
async def client_get_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(authentication.get_current_user),
):
    result = await db.execute(select(Client).where(Client.username == username))
    result = result.scalar_one_or_none()

    if result:
        return ClientAllInfo(
            uuid=result.uuid,
            username=result.username,
            ip_address=result.ip_address,
            hostname=result.hostname,
            alive=result.alive,
            last_contact=result.last_contact,
            last_known_location=result.last_known_location,
            client_version=result.client_version,
        )

    raise HTTPException(status_code=404, detail="Client not found")


@router.get("/all", response_model=ClientAllResponse)
async def client_all(
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user)
):
    result = await db.execute(select(Client))
    clients = result.scalars().all()

    client_list = []
    for client in clients:
        client_info = BasicClientInfo(
            username=client.username,
            ip_address=client.ip_address,
            hostname=client.hostname,
            alive=client.alive,
            last_contact=client.last_contact,
        )
        client_list.append(client_info)

    return ClientAllResponse(clients=client_list)


@router.get("/update")
async def client_update(client: Client = Depends(get_current_client)):
    if client.client_version >= settings.app.client_version:
        raise HTTPException(status_code=400, detail="Client already at latest version")

    client_binary_ext = ".exe" if platform.system() == "Windows" else ""
    client_binary = (
        Path(settings.paths.client_dir) / "target" / f"client{client_binary_ext}"
    )
    if not os.path.isfile(client_binary):
        raise HTTPException(status_code=500, detail="Unable to find client binary")

    return FileResponse(
        path=client_binary,
        filename=f"client{client_binary_ext}",
        media_type="application/octet-stream",
    )


@router.post("/update-info")
async def client_update_info(
    update_info: ClientUpdateInfo,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    update_data = update_info.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    try:
        await db.commit()
        await db.refresh(client)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to add updated information to the database"
        )

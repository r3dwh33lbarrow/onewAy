import os.path
import platform
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.dependencies import get_db
from app.models.client import Client
from app.schemas.client import ClientAllResponse, BasicClientInfo, ClientUpdateInfo, ClientAllInfo
from app.services import authentication
from app.services.authentication import get_current_client
from app.settings import settings

router = APIRouter(prefix="/client")


@router.get("/get/{username}", response_model=ClientAllInfo)
async def client(username: str, db: AsyncSession = Depends(get_db), _=Depends(authentication.verify_access_token)):
    result = await db.execute(select(Client).where(Client.username == username))
    result = result.scalar_one_or_none()

    if result:
        return ClientAllInfo(
            uuid=str(result.uuid),
            username=result.username,
            ip_address=result.ip_address,
            hostname=result.hostname if result.hostname else "",
            alive=result.alive,
            last_contact=str(result.last_contact),
            last_known_location=result.last_known_location if result.last_known_location else "",
            client_version=result.client_version
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Client not found"
    )


@router.get("/all", response_model=ClientAllResponse)
async def client_all(db: AsyncSession = Depends(get_db), _=Depends(authentication.verify_access_token)):
    """
    Retrieve all clients from the database.

    Returns:
        ClientAllResponse: A response containing a list of all clients with their basic information.
    """
    result = await db.execute(select(Client))
    clients = result.scalars().all()

    client_list = []
    for client in clients:
        client_info = BasicClientInfo(
            username=client.username,
            ip_address=client.ip_address,
            hostname=client.hostname or "",
            alive=client.alive,
            last_contact=client.last_contact.isoformat() if client.last_contact else ""
        )
        client_list.append(client_info)

    return ClientAllResponse(clients=client_list)


@router.get("/update")
async def client_update(client: Client = Depends(get_current_client)):
    if client.client_version >= settings.version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client already at latest version"
        )

    client_binary_ext = ".exe" if platform.system() == "Windows" else ""
    client_binary = Path(settings.client_directory) / "target" / f"client{client_binary_ext}"
    if not os.path.isfile(client_binary):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to find client binary"
        )

    return FileResponse(path=client_binary, filename=f"client{client_binary_ext}", media_type="application/octet-stream")


@router.post("/update-info")
async def client_update_info(update_info: ClientUpdateInfo,
                             client: Client = Depends(get_current_client),
                             db: AsyncSession = Depends(get_db)):
    if update_info.ip_address:
        client.client_version = update_info.ip_address
    if update_info.hostname:
        client.hostname = update_info.hostname
    if update_info.last_known_location:
        client.last_known_location = update_info.last_known_location
    if update_info.client_version:
        client.client_version = update_info.client_version

    try:
        await db.commit()
        await db.refresh(client)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add updated information to the database"
        )

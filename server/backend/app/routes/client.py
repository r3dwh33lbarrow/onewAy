import os.path
import platform
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.client import Client
from app.schemas.client import *
from app.schemas.general import BasicTaskResponse
from app.services import authentication
from app.services.authentication import get_current_client, get_current_user
from app.settings import settings

router = APIRouter(prefix="/client")


@router.get("/me", response_model=ClientMeResponse)
async def client_me(client: Client = Depends(authentication.get_current_client)):
    """
    Get username from the currently authenticated client.

    Args:
        client: Currently authenticated client

    Returns:
        Basic client username
    """
    return ClientMeResponse(username=client.username)


@router.get("/get/{username}", response_model=ClientAllInfo)
async def client_get_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(authentication.get_current_user),
):
    """
    Retrieve detailed information for a specific client by username.

    Args:
        username: The unique username of the client to retrieve
        db: Database session for executing queries
        _: Current authenticated user (required for authorization)

    Returns:
        Complete client information including UUID, network details, and status

    Raises:
        HTTPException: 404 if client not found
    """
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
async def client_all(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """
    Retrieve a list of all registered clients with basic information.

    Args:
        db: Database session for executing queries
        _: Current authenticated user (required for authorization)

    Returns:
        List of clients with basic info (username, IP, hostname, status, last contact)
    """
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
    """
    Download the latest client binary for updating.

    Args:
        client: Currently authenticated client requesting the update

    Returns:
        Client binary file appropriate for the client's platform

    Raises:
        HTTPException: 400 if client is already up to date, 500 if binary not found
    """
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


@router.post("/update-info", response_model=BasicTaskResponse)
async def client_update_info(
    update_info: ClientUpdateInfo,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """
    Update client information in the database.

    Args:
        update_info: Client data to update (only provided fields will be updated)
        client: Currently authenticated client to update
        db: Database session for executing queries

    Returns:
        Success status of the update operation

    Raises:
        HTTPException: 500 if database update fails
    """
    update_data = update_info.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    try:
        await db.commit()
        await db.refresh(client)
        return {"result": "success"}
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to add updated information to the database"
        )

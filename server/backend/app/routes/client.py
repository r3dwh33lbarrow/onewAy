import os.path
import platform
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.logger import get_logger
from app.models.client import Client
from app.models.refresh_token import RefreshToken
from app.schemas.client import *
from app.schemas.general import BasicTaskResponse
from app.services.authentication import (
    any_valid_refresh_tokens,
    get_current_client,
    get_current_user,
    is_client,
    verify_access_token,
)
from app.services.client_websockets import client_websocket_manager
from app.services.password import hash_password
from app.settings import settings

router = APIRouter(prefix="/client")
logger = get_logger()


@router.get("/me", response_model=ClientMeResponse)
async def client_me(client: Client = Depends(get_current_client)):
    """
    Get username from the currently authenticated client.

    Args:
        client: Currently authenticated client

    Returns:
        Basic client username
    """
    logger.debug("Client self lookup for %s", client.username)
    return ClientMeResponse(username=client.username)


@router.get("/action/{username}", response_model=ClientAllInfo)
async def client_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_access_token),
):
    """
    Retrieve detailed information for a specific client by username.

    Args:
        username: The unique username of the client to retrieve
        db: Database session for executing queries
        _: Current authenticated user or client

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
            client_version=result.client_version,
             platform=result.platform,
            any_valid_tokens=await any_valid_refresh_tokens(result.uuid, db),
        )
    logger.warning("Client lookup failed for username '%s'", username)
    raise HTTPException(status_code=404, detail="Client not found")


@router.delete("/action/{username}", response_model=BasicTaskResponse)
async def client_delete_username(
    username: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)
):
    client = await db.execute(select(Client).where(Client.username == username))
    client = client.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=400, detail="Client not found")

    try:
        await db.delete(client)
        await db.commit()
        return {"result": "success"}
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{username}/revoke-tokens", response_model=BasicTaskResponse)
async def revoke_client_refresh_tokens(
    username: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_access_token),
):
    """
    Revoke all refresh tokens for a specific client.

    Users can revoke tokens for any client.
    Clients can only revoke their own tokens.

    Args:
        username: The username of the client whose tokens should be revoked
        request: The incoming request to determine if requester is user or client
        db: Database session for executing queries
        _: Current authenticated user or client

    Returns:
        Success status of the revocation operation

    Raises:
        HTTPException: 404 if client not found, 403 if client tries to revoke another client's tokens
    """
    result = await db.execute(select(Client).where(Client.username == username))
    target_client = result.scalar_one_or_none()

    if not target_client:
        logger.warning("Token revocation failed: client '%s' not found", username)
        raise HTTPException(status_code=404, detail="Client not found")

    if is_client(request):
        result = await db.execute(select(Client).where(Client.uuid == uuid.UUID(_)))
        requesting_client = result.scalar_one_or_none()

        if not requesting_client or requesting_client.uuid != target_client.uuid:
            logger.warning(
                "Client '%s' attempted to revoke tokens for another client '%s'",
                requesting_client.username if requesting_client else "unknown",
                username,
            )
            raise HTTPException(
                status_code=403,
                detail="Clients can only revoke their own refresh tokens",
            )

    try:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.client_uuid == target_client.uuid,
                RefreshToken.revoked == False,
            )
        )
        tokens = result.scalars().all()

        revoked_count = 0
        for token in tokens:
            token.revoked = True
            revoked_count += 1

        target_client.revoked = True
        target_client.alive = False
        target_client.hashed_password = hash_password(uuid.uuid4().hex)

        await db.commit()
        logger.info(
            "Revoked %d refresh token(s) for client '%s'",
            revoked_count,
            username,
        )

        await client_websocket_manager.disconnect_all(str(target_client.uuid))
        await client_websocket_manager.broadcast_client_alive_status(
            target_client.username, alive=False
        )
        return {"result": "success"}

    except SQLAlchemyError as e:
        await db.rollback()
        logger.exception("Failed to revoke tokens for client '%s'", username)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/get-all", response_model=ClientAllResponse)
async def client_all(
    db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)
):
    """
    Retrieve a list of all registered clients with basic information.

    Args:
        db: Database session for executing queries
        _: Current authenticated user or client

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
            platform=client.platform,
        )
        client_list.append(client_info)

    logger.debug("Fetched %d clients", len(client_list))
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
        logger.info(
            "Client '%s' attempted update but already on latest version",
            client.username,
        )
        raise HTTPException(status_code=400, detail="Client already at latest version")

    client_binary_ext = ".exe" if platform.system() == "Windows" else ""
    client_binary = (
        Path(settings.paths.client_dir) / "target" / f"client{client_binary_ext}"
    )
    logger.debug(
        "Client '%s' requesting update binary %s",
        client.username,
        client_binary,
    )
    if not os.path.isfile(client_binary):
        logger.error("Client binary missing at %s", client_binary)
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
    client_username = client.username

    update_payload = update_info.model_dump(exclude_unset=True)
    update_data = {
        field: value
        for field, value in update_payload.items()
        if value is not None
    }

    if "platform" in update_data:
        platform_value = str(update_data["platform"]).lower()
        if platform_value not in {"windows", "mac", "linux"}:
            raise HTTPException(
                status_code=400,
                detail="Unsupported platform. Allowed values: windows, mac, linux.",
            )
        update_data["platform"] = platform_value

    for field, value in update_data.items():
        setattr(client, field, value)

    try:
        await db.commit()
        await db.refresh(client)
        logger.info("Client '%s' updated info", client_username)
        logger.debug("Client '%s' update payload: %s", client_username, update_data)
        return {"result": "success"}
    except Exception:
        await db.rollback()
        logger.exception("Failed to persist update for client '%s'", client_username)
        raise HTTPException(
            status_code=500, detail="Failed to add updated information to the database"
        )

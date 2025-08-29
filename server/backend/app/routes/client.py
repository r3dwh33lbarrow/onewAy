from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.client import Client
from app.schemas.client import ClientAllResponse, BasicClientInfo
from app.schemas.general import BasicTaskResponse
from app.services import authentication
from app.services.authentication import get_current_client
from app.settings import settings

router = APIRouter(prefix="/client")


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


@router.get("/update", response_model=BasicTaskResponse)
async def client_update(client: Client = Depends(get_current_client)):
    if client.client_version >= settings.version:
        return {"result": "client already updated"}

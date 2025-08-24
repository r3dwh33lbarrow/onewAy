from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.client import Client
from app.schemas.client import ClientAllResponse, BasicClientInfo
from app.services import authentication

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

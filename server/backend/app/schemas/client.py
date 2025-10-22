from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, IPvAnyAddress


class BasicClientInfo(BaseModel):
    username: str
    ip_address: IPvAnyAddress | None = None
    hostname: str | None = None
    alive: bool
    last_contact: datetime | None = None


class ClientAllResponse(BaseModel):
    clients: List[BasicClientInfo]


class ClientUpdateInfo(BaseModel):
    ip_address: IPvAnyAddress | None = None
    hostname: str | None = None
    last_known_location: str | None = None
    client_version: str | None = None


class ClientAllInfo(BasicClientInfo):
    uuid: UUID
    last_known_location: str | None = None
    client_version: str = Field(min_length=1)


class ClientMeResponse(BaseModel):
    username: str = Field(min_length=1)

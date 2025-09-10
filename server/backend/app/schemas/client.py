from pydantic import BaseModel
from typing import List, Optional


class BasicClientInfo(BaseModel):
    username: str
    ip_address: str
    hostname: str
    alive: bool
    last_contact: str


class ClientAllResponse(BaseModel):
    clients: List[BasicClientInfo]


class ClientUpdateInfo(BaseModel):
    ip_address: Optional[str]
    hostname: Optional[str]
    last_known_location: Optional[str]
    client_version: Optional[str]


class ClientAllInfo(BaseModel):
    uuid: str
    username: str
    ip_address: str
    hostname: str
    alive: bool
    last_contact: str
    last_known_location: str
    client_version: str

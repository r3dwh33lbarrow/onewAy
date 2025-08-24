from pydantic import BaseModel
from typing import List


class BasicClientInfo(BaseModel):
    username: str
    ip_address: str
    hostname: str
    alive: bool
    last_contact: str


class ClientAllResponse(BaseModel):
    clients: List[BasicClientInfo]

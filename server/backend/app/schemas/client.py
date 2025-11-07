from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.utils import normalize_hostname_or_ip


class BasicClientInfo(BaseModel):
    username: str
    ip_address: str | None = None
    hostname: str | None = None
    alive: bool
    last_contact: datetime | None = None
    platform: str | None = None

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            return normalize_hostname_or_ip(value)
        except ValueError as exc:
            raise ValueError(
                "ip_address must be a valid IP address or hostname"
            ) from exc


class ClientAllResponse(BaseModel):
    clients: List[BasicClientInfo]


class ClientUpdateInfo(BaseModel):
    ip_address: str | None = None
    hostname: str | None = None
    client_version: str | None = None
    platform: str | None = None

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            return normalize_hostname_or_ip(value)
        except ValueError as exc:
            raise ValueError(
                "ip_address must be a valid IP address or hostname"
            ) from exc


class ClientAllInfo(BasicClientInfo):
    uuid: UUID
    client_version: str = Field(min_length=1)
    any_valid_tokens: bool


class ClientMeResponse(BaseModel):
    username: str = Field(min_length=1)

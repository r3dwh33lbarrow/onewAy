from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BucketInfo(BaseModel):
    name: str = Field(..., min_length=1)
    consumed: bool
    created_at: datetime
    client_username: str | None = None
    entry_uuid: UUID | None = None


class BucketData(BaseModel):
    data: str


class BucketEntry(BaseModel):
    uuid: UUID
    client_username: str | None = None
    data: str
    consumed: bool
    created_at: datetime
    remove_at: datetime | None = None


class ModuleBucketResponse(BaseModel):
    module_name: str
    entries: list[BucketEntry]


class AllBucketsResponse(BaseModel):
    buckets: list[BucketInfo]

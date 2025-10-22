from datetime import datetime

from pydantic import BaseModel, Field


class BucketInfo(BaseModel):
    name: str = Field(..., min_length=1)
    consumed: bool
    created_at: datetime


class BucketData(BaseModel):
    data: str


class AllBucketsResponse(BaseModel):
    buckets: list[BucketInfo]

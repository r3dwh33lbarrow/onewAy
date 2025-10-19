from pydantic import BaseModel, Field
from datetime import datetime


class BucketInfo(BaseModel):
    name: str = Field(..., min_length=1)
    consumed: bool
    created_at: datetime

class BucketData(BaseModel):
    data: str


class AllBucketsResponse(BaseModel):
    buckets: list[BucketInfo]

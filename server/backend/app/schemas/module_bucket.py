from pydantic import BaseModel


class BucketData(BaseModel):
    data: str


class AllBucketsResponse(BaseModel):
    buckets: dict[str, str]

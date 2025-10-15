from pydantic import BaseModel


class BucketInfo(BaseModel):
    data: str
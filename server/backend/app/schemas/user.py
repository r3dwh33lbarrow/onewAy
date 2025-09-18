from datetime import datetime

from pydantic import BaseModel, Field


class UserInfoResponse(BaseModel):
    username: str
    is_admin: bool
    last_login: datetime
    created_at: datetime
    avatar_set: bool


class UserUpdateRequest(BaseModel):
    username: str | None = Field(None, min_length=1)

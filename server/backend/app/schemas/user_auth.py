from pydantic import BaseModel, Field


class UserSignupRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserSigninRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

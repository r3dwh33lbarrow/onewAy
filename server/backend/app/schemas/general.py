from pydantic import BaseModel


class BasicTaskResponse(BaseModel):
    result: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"

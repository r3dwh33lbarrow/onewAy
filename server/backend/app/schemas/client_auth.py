from pydantic import BaseModel


class ClientEnrollRequest(BaseModel):
    username: str
    password: str
    client_version: str


class ClientLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"

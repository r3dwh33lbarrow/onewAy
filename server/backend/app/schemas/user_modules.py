from pydantic import BaseModel, Field


class ModuleInfo(BaseModel):
    name: str = Field(min_length=1)
    path: str = Field(min_length=1)
    version: str = Field(min_length=1)


class UserModuleAllResponse(BaseModel):
    modules: list[ModuleInfo]
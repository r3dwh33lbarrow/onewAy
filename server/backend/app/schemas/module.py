from typing import Any

from pydantic import BaseModel, Field


class ModuleBasicInfo(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    version: str = Field(min_length=1)
    start: str = Field(min_length=1)
    binaries_platform: list[str]


class UserModuleAllResponse(BaseModel):
    modules: list[ModuleBasicInfo]


class ModuleInfo(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    version: str = Field(min_length=1)
    start: str = Field(min_length=1)
    binaries: dict[str, Any]


class ModuleAddRequest(BaseModel):
    module_path: str = Field(min_length=1)


class ModuleDirectoryContents(BaseModel):
    contents: list[dict[str, str]] | None = None


class InstalledModuleInfo(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    version: str = Field(min_length=1)
    status: str | None = None


class AllInstalledResponse(BaseModel):
    all_installed: list[InstalledModuleInfo] | None = None

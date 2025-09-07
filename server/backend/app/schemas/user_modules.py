from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class ModuleBasicInfo(BaseModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None
    version: str = Field(min_length=1)
    binaries_platform: List[str]


class UserModuleAllResponse(BaseModel):
    modules: list[ModuleBasicInfo]


class ModuleInfo(BaseModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None
    version: str = Field(min_length=1)
    start: str = Field(min_length=1)
    binaries: Dict[str, Any]


class ModuleAddRequest(BaseModel):
    module_path: str = Field(min_length=1, description="Path to the module directory")


class ModuleDirectoryContents(BaseModel):
    contents: Optional[list[dict[str, str]]] = None

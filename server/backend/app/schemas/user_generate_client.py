from typing import List, Literal, Optional

from pydantic import BaseModel, Field, IPvAnyAddress


class GenerateClientRequest(BaseModel):
    platform: Literal["windows", "mac", "linux"]
    ip_address: IPvAnyAddress
    port: int = Field(..., ge=1, le=65535)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    packaged_modules: List[str] = Field(default_factory=list)
    output_override: Optional[bool]
    debug: Optional[bool]


class VerifyRustResponse(BaseModel):
    rust_installed: bool
    cargo_installed: bool
    windows_target_installed: bool
    mac_target_installed: bool
    linux_target_installed: bool

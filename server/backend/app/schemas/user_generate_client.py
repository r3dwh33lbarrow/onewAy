from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils import normalize_hostname_or_ip


class GenerateClientRequest(BaseModel):
    platform: Literal["windows", "mac", "linux"]
    ip_address: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    packaged_modules: List[str] = Field(default_factory=list)
    output_override: Optional[bool]
    debug: Optional[bool]

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str) -> str:
        try:
            return normalize_hostname_or_ip(value)
        except ValueError as exc:
            raise ValueError(
                "IP address must be a valid IP address or hostname"
            ) from exc


class VerifyRustResponse(BaseModel):
    rust_installed: bool
    cargo_installed: bool
    windows_target_installed: bool
    mac_target_installed: bool
    linux_target_installed: bool

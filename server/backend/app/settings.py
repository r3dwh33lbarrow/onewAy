import tomllib
from pathlib import Path
from typing import List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

from app.utils import resolve_root

CONFIG_PATH = Path(resolve_root("[ROOT]")) / "server" / "backend" / "config.toml"


def toml_settings() -> dict:
    try:
        with open(CONFIG_PATH, "rb") as file:
            return tomllib.load(file)
    except FileNotFoundError:
        raise RuntimeError("Could not find config.toml")


class AppSettings(BaseSettings):
    debug: bool = Field(False)
    client_version: str = Field("")


class CorsSettings(BaseSettings):
    allow_origins: List[str] = Field(["http://localhost:5173", "http://127.0.0.1:5173"])


class DatabaseSettings(BaseSettings):
    url: str = Field(min_length=1)
    pool_size: int = Field(10)
    pool_timeout: int = Field(30)
    echo: bool = Field(False)


class SecuritySettings(BaseSettings):
    secret_key: str = Field(min_length=1)
    algorithm: str = Field("HS256")
    access_token_expires_minutes: int = Field(15)
    refresh_token_expires_days: int = Field(7)
    jwt_issuer: str = Field("https://api.oneway.local")
    jwt_audience: str = Field("oneway-api")


class TestingDatabaseSettings(BaseSettings):
    url: str = Field("")
    pool_size: int = Field(10)
    pool_timeout: int = Field(30)
    echo: bool = Field(False)


class TestingSecuritySettings(BaseSettings):
    secret_key: str = Field("")
    algorithm: str = Field("HS256")
    access_token_expires_minutes: int = Field(15)
    refresh_token_expires_days: int = Field(7)


class TestingSettings(BaseSettings):
    testing: bool = Field(False)
    database: TestingDatabaseSettings
    security: TestingSecuritySettings


class PathSettings(BaseSettings):
    client_dir: str = Field("[ROOT]/client")
    module_dir: str = Field("[ROOT]/modules")
    avatar_dir: str = Field("[ROOT]/server/backend/app/resources")


class OtherSettings(BaseSettings):
    max_avatar_size_mb: int = Field(2)


class Settings(BaseSettings):
    app: AppSettings
    cors: CorsSettings
    database: DatabaseSettings
    security: SecuritySettings
    testing: TestingSettings
    paths: PathSettings
    other: OtherSettings

    model_config = {"extra": "ignore", "frozen": True}

    @model_validator(mode="after")
    def _resolve_paths(self) -> "Settings":
        """Resolve [ROOT] placeholders in path settings to actual paths."""
        self.paths.client_dir = resolve_root(self.paths.client_dir)
        self.paths.module_dir = resolve_root(self.paths.module_dir)
        self.paths.default_avatar = resolve_root(self.paths.default_avatar)
        return self

    @model_validator(mode="after")
    def _testing_check(self) -> "Settings":
        """Validates all required fields are filled if testing"""
        if self.testing.testing and not self.testing.database.url:
            raise RuntimeError(
                "[ERROR in config.yaml] You must provide a testing database URL if testing"
            )
        if self.testing.testing and not self.testing.security.algorithm:
            raise RuntimeError(
                "[ERROR in config.yaml] You must provide a testing secret key if testing"
            )

        return self

    @model_validator(mode="after")
    def _check_required(self) -> "Settings":
        if not self.app.client_version.strip():
            raise RuntimeError(
                "[ERROR in config.yaml] You must provide a client version"
            )
        return self


settings = Settings(**toml_settings())

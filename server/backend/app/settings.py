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


class CorsSettings(BaseSettings):
    allow_origins: List[str] = Field(["http://localhost:5173", "http://127.0.0.1:5173"])


class DatabaseSettings(BaseSettings):
    url: str = Field(min_length=1)
    pool_size: int = Field(10)
    pool_timeout: int = Field(30)
    echo_sql: bool = Field(False)


class SecuritySettings(BaseSettings):
    secret_key: str = Field(min_length=1)
    algorithm: str = Field("HS256")
    access_token_expires_minutes: int = Field(15)
    refresh_token_expires_days: int = Field(7)


class TestingSettings(BaseSettings):
    testing: bool = Field(False)
    testing_db_url: str = Field("")
    testing_db_secret_key: str = Field("")


class PathSettings(BaseSettings):
    client_dir: str = Field("[ROOT]/client")
    module_dir: str = Field("[ROOT]/modules")


class Settings(BaseSettings):
    debug: bool = Field(False)
    cors: CorsSettings
    database: DatabaseSettings
    security: SecuritySettings
    testing: TestingSettings
    paths: PathSettings

    model_config = {
        "extra": "ignore",
        "frozen": True
    }

    @model_validator(mode="after")
    def _resolve_paths(self) -> "Settings":
        """Resolve [ROOT] placeholders in path settings to actual paths."""
        self.paths.client_dir = resolve_root(self.paths.client_dir)
        self.paths.module_dir = resolve_root(self.paths.module_dir)
        return self


    @model_validator(mode="after")
    def _testing_check(self) -> "Settings":
        """Validates all required fields are filled if testing"""
        if self.testing.testing and not self.testing.testing_db_url:
            raise RuntimeError("You must provide a testing database URL if testing")
        if  self.testing.testing and not self.testing.testing_db_secret_key:
            raise RuntimeError("You must provide a testing secret key if testing")

        return self


settings = Settings(**toml_settings())

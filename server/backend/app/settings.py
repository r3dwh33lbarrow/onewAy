import tomllib

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

from app.utils import resolve_root


def toml_settings(_settings: BaseSettings) -> dict:
    try:
        with open("config.toml", "rb") as file:
            return tomllib.load(file)
    except FileNotFoundError:
        raise RuntimeError("Could not find config.toml")


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


class PathSettings(BaseSettings):
    client_dir: str = Field("[ROOT]/client")
    module_dir: str = Field("[ROOT]/modules")


class Settings(BaseSettings):
    debug: bool = Field(False)
    database: DatabaseSettings
    security: SecuritySettings
    paths: PathSettings

    class Config:
        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            return init_settings, toml_settings, env_settings, file_secret_settings

    @model_validator(mode="after")
    def _resolve_paths(self) -> "Settings":
        """Resolve [ROOT] placeholders in path settings to actual paths."""
        self.paths.client_dir = resolve_root(self.paths.client_dir)
        self.paths.module_dir = resolve_root(self.paths.module_dir)
        return self


settings = Settings()  # type: ignore
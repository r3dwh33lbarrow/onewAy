from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

from app.logger import get_logger

log = get_logger()


class Settings(BaseSettings):
    # Database settings
    database_url: str = Field(..., alias="DATABASE_URL")

    # Security settings
    secret_key: str = Field(..., alias="SECRET_KEY")

    # Testing settings
    testing: bool = Field(False, alias="TESTING")

    # JWT settings
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # Module settings
    module_path: Optional[str] = None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
        "populate_by_name": True,
    }


def load_test_settings(path_env_test: str = "tests/.env.test") -> Settings:
    """Return a new Settings instance with test configuration"""
    log.info("Loading test settings")

    # Create a new settings object with test values
    test_settings = Settings()

    with open(path_env_test, "r") as env_file:
        for line in env_file:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                if key == "TEST_DATABASE_URL":
                    test_settings.database_url = value
                if key == "SECRET_KEY":
                    test_settings.secret_key = value

    test_settings.testing = True
    return test_settings


settings = Settings()

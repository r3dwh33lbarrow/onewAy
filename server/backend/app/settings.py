import os
from pydantic import Field, model_validator
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
    # Production modules directory (default); tests use a separate path
    module_path_prod: str = Field("[ROOT]" + os.sep + "modules", alias="MODULE_DIRECTORY")
    # Test modules directory (cleaned by tests)
    module_path_test: str = Field("[ROOT]" + os.sep + "server" + os.sep + "backend" + os.sep + "app" + os.sep + "modules", alias="TEST_MODULE_DIRECTORY")
    # Effective modules directory used by the app (computed in validator)
    module_path: str = "[ROOT]" + os.sep + "modules"
    client_directory: str = Field("[ROOT]" + os.sep + "client", alias="CLIENT_DIRECTORY")

    avatar_directory: str = Field("[ROOT]" + os.sep + "server" + os.sep + "backend" + os.sep + "app" + os.sep + "resources" + os.sep + "avatars", alias="AVATAR_DIRECTORY")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
        "populate_by_name": True,
    }

    @model_validator(mode="after")
    def _resolve_paths(self) -> "Settings":
        from app.utils import resolve_root
        prod = resolve_root(self.module_path_prod)
        test = resolve_root(self.module_path_test)
        # Heuristics: prefer test path when explicitly testing
        is_pytest = bool(os.getenv("PYTEST_CURRENT_TEST"))
        has_test_db = bool(os.getenv("TEST_DATABASE_URL"))
        use_test = self.testing or is_pytest or has_test_db
        self.module_path = test if use_test else prod
        self.client_directory = resolve_root(self.client_directory)
        self.avatar_directory = resolve_root(self.avatar_directory)
        return self


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

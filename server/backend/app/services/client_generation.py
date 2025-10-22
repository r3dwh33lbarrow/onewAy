import os
import shutil
import subprocess
from pathlib import Path

import tomli_w

from app.logger import get_logger
from app.settings import settings
from app.utils import convert_to_snake_case
from app.version import __version__

log = get_logger()


def generate_client_config(path: Path, username: str, password: str) -> None:
    data = {
        "module": {
            "version": __version__,
            "modules_directory": "[CURRENT_DIRECTORY]/modules",
        },
        "auth": {
            "username": username,
            "password": password,
        },
    }

    with open(path / "config.toml", "wb+") as file:
        tomli_w.dump(data, file)


def move_modules(path: Path, module_list: list[str]) -> None:
    modules_dir = path / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)

    for module in module_list:
        module_snake_case = convert_to_snake_case(module)
        module_source = Path(settings.paths.module_dir) / module_snake_case

        if not module_source.is_dir():
            raise RuntimeError("Not a valid module path")

        if not (module_source / "config.yaml").is_file():
            raise RuntimeError("Module directory does not contain config.yaml")

        shutil.copytree(
            module_source, modules_dir / module_snake_case, dirs_exist_ok=True
        )


def generate_client_binary(path: Path, platform: str, ip: str, port: int) -> None:
    if platform == "windows":
        extension = ".exe"
    elif platform == "mac":
        extension = ""
    else:
        raise RuntimeError("Incompatible platform")

    try:
        subprocess.run(
            ["cargo", "build", "--release"],
            check=True,
            text=True,
            capture_output=True,
            cwd=settings.paths.client_dir,
            env={**os.environ, "IP": ip, "PORT": str(port)},
        )
    except subprocess.CalledProcessError as exc:
        log.error(
            "Failed to compile client binary - stdout: %s stderr: %s",
            exc.stdout,
            exc.stderr,
        )
        raise RuntimeError("Failed to compile client binary - check server logs") from exc

    binary_source = Path(settings.paths.client_dir) / "target" / "release" / f"client{extension}"
    binary_destination = path / f"client{extension}"
    shutil.copy2(binary_source, binary_destination)

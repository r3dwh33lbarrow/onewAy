import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

import tomli_w
import yaml

from app.logger import get_logger
from app.settings import settings
from app.utils import convert_to_snake_case
from app.version import __version__

log = get_logger()


def generate_client_config(
    path: Path,
    username: str,
    password: str,
    debug: bool | None = None,
    output_override: bool | None = None,
) -> None:
    data = {
        "module": {
            "version": __version__,
            "modules_directory": "[CURRENT_DIR]/modules",
        },
        "auth": {
            "username": username,
            "password": password,
        },
    }
    if output_override and debug is not None:
        data = {"debug": debug, "output_override": True, **data}

    if output_override and debug is None:
        data = {"output_override": True, **data}

    with open(path / "config.toml", "wb+") as file:
        tomli_w.dump(data, file)


def move_modules(path: Path, platform: str, module_list: list[str]) -> None:
    modules_dir = path / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)

    for module in module_list:
        module_snake_case = convert_to_snake_case(module)
        module_source = Path(settings.paths.module_dir) / module_snake_case

        if not module_source.is_dir():
            raise RuntimeError("Not a valid module path")

        config_path = module_source / "config.yaml"
        if not config_path.is_file():
            raise RuntimeError("Module directory does not contain config.yaml")

        try:
            with config_path.open("r", encoding="utf-8") as config_file:
                config_data = yaml.safe_load(config_file)
        except yaml.YAMLError as exc:
            raise RuntimeError(
                f"Failed to parse config.yaml for module '{module}'"
            ) from exc

        module_destination = modules_dir / module_snake_case
        module_destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_path, module_destination / "config.yaml")

        binaries = config_data.get("binaries", {})
        if isinstance(binaries, str):
            try:
                binaries = json.loads(binaries)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Module '{module}' contains an invalid binaries definition"
                ) from exc

        if not isinstance(binaries, dict):
            raise RuntimeError(
                f"Module '{module}' binaries must be defined as a mapping"
            )

        binary_entry = binaries.get(platform)
        if not binary_entry:
            raise RuntimeError(
                f"Module '{module}' does not provide a binary for platform '{platform}'"
            )

        binary_path = Path(binary_entry)
        if binary_path.is_absolute():
            raise RuntimeError(
                f"Module '{module}' binary path must be relative for packaging"
            )

        binary_source = (module_source / binary_path).resolve()
        if not binary_source.exists() or not binary_source.is_file():
            raise RuntimeError(
                f"Binary '{binary_entry}' for module '{module}' does not exist"
            )

        # Prevent escaping the module directory via paths like ../
        if module_source not in binary_source.parents:
            raise RuntimeError(
                f"Binary '{binary_entry}' for module '{module}' must reside within the module directory"
            )

        binary_destination = module_destination / binary_path
        binary_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary_source, binary_destination)


def compile_client(path: Path, platform_target: str, ip: str, port: int) -> None:
    build_command = ["cargo", "build", "--release"]

    if platform_target == "windows":
        extension = ".exe"
        target_triple = "x86_64-pc-windows-gnu"
    elif platform_target == "mac":
        extension = ""
        target_triple = "aarch64-apple-darwin"
    elif platform_target == "linux":
        extension = ""
        if "macos" in platform.platform().lower():
            target_triple = "x86_64-unknown-linux-musl"
        else:
            target_triple = "x86_64-unknown-linux-gnu"
    else:
        raise RuntimeError("Incompatible platform")

    build_command.extend(["--target", target_triple])

    try:
        subprocess.run(
            build_command,
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
        raise RuntimeError(
            "Failed to compile client binary - check server logs"
        ) from exc

    binary_source = (
        Path(settings.paths.client_dir)
        / "target"
        / target_triple
        / "release"
        / f"client{extension}"
    )
    binary_destination = path / f"client{extension}"
    shutil.copy2(binary_source, binary_destination)

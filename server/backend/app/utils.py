import re
from pathlib import Path

from app.logger import get_logger

log = get_logger()


def convert_to_snake_case(string: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]", " ", string)
    words = s.lower().split()
    return "_".join(words)


def hyphen_to_snake_case(string: str) -> str:
    return string.replace("-", "_").lower()


def resolve_root(path: str) -> str:
    try:
        # Use pathlib for cross-platform path handling
        root = Path(__file__).resolve().parent.parent.parent.parent
        # Replace [ROOT] with the actual root path and normalize
        resolved_path = path.replace("[ROOT]", str(root))
        return str(Path(resolved_path))
    except Exception as e:
        log.error("Failed to parse [ROOT] from config: " + str(e))
        return path

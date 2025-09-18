import re
from pathlib import Path


def convert_to_snake_case(string: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]", " ", string)
    words = s.lower().split()
    return "_".join(words)


def hyphen_to_snake_case(string: str) -> str:
    return string.replace("-", "_").lower()


def resolve_root(path: str) -> str:
    """
    Replace [ROOT] placeholder with the project root directory path.

    The root directory is four levels up from this file's location.
    """
    try:
        root = Path(__file__).resolve().parent.parent.parent.parent
        resolved_path = path.replace("[ROOT]", str(root))
        return str(Path(resolved_path))
    except Exception as e:
        raise RuntimeError("Failed to parse [ROOT] from config: " + str(e))

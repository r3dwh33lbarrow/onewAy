import ipaddress
import re
from pathlib import Path


def convert_to_snake_case(string: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]", " ", string)
    words = s.lower().split()
    return "_".join(words)


def hyphen_to_snake_case(string: str) -> str:
    return string.replace("-", "_").lower()


def convert_to_title_case(string: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", string) if p]
    titled = [p[:1].upper() + p[1:].lower() if p else "" for p in parts]
    return " ".join(titled)


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


_HOSTNAME_SEGMENT_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")
_SINGLE_HOST_PREFIXES = {"32", "128"}


def _normalize_ip(candidate: str) -> str | None:
    """
    Attempt to normalize the candidate as an IP address, optionally with a host prefix.
    Returns the normalized IP string on success, otherwise None.
    """
    try:
        return ipaddress.ip_address(candidate).compressed
    except ValueError:
        pass

    if "/" in candidate:
        address, prefix = candidate.split("/", 1)
        if prefix in _SINGLE_HOST_PREFIXES:
            try:
                return ipaddress.ip_address(address).compressed
            except ValueError:
                return None
    return None


def normalize_hostname_or_ip(value: str) -> str:
    """
    Validate and normalize an IP address or hostname.

    Returns the normalized value or raises ValueError when invalid.
    """
    candidate = value.strip()
    if not candidate:
        raise ValueError("Value must not be empty")

    ip_value = _normalize_ip(candidate)
    if ip_value is not None:
        return ip_value

    if candidate.endswith("."):
        candidate = candidate[:-1]

    if not candidate or len(candidate) > 253:
        raise ValueError("Value must be a valid IP address or hostname")

    if not all(_HOSTNAME_SEGMENT_RE.match(segment) for segment in candidate.split(".")):
        raise ValueError("Value must be a valid IP address or hostname")

    return candidate


def is_valid_hostname_or_ip(value: str) -> bool:
    """
    Convenience helper to check whether the value is a valid IP address or hostname.
    """
    try:
        normalize_hostname_or_ip(value)
        return True
    except ValueError:
        return False

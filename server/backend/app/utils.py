import re


def convert_to_snake_case(string: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]', ' ', string)
    words = s.lower().split()
    return '_'.join(words)


def hyphen_to_snake_case(string: str) -> str:
    return string.replace('-', '_').lower()

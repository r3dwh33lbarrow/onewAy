from app.utils import convert_to_snake_case, hyphen_to_snake_case, resolve_root


def test_convert_to_snake_case_basic():
    assert convert_to_snake_case("Hello World!") == "hello_world"
    assert convert_to_snake_case("Already_Snake-Case 123") == "already_snake_case_123"


def test_hyphen_to_snake_case():
    assert hyphen_to_snake_case("my-module-name") == "my_module_name"
    assert hyphen_to_snake_case("NoHyphens") == "nohyphens"


def test_resolve_root_placeholder():
    s = resolve_root("[ROOT]/some/path")
    # Should replace [ROOT] and return an absolute-like path containing 'some/path'
    assert "some/path" in s or "some\\path" in s


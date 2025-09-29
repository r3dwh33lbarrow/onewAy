from app.services.password import hash_password, verify_password


def test_hash_and_verify_password_roundtrip():
    pw = "secret123!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed)
    assert not verify_password("wrong", hashed)


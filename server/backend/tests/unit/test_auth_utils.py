import uuid

import pytest
from jose import jwt

from app.services.authentication import (
    TokenType,
    create_access_token,
    hash_jti,
    verify_jti,
    verify_websocket_access_token,
)
from app.settings import settings


def test_create_access_token_and_decode():
    uid = uuid.uuid4()
    token = create_access_token(uid, TokenType.CLIENT)
    decoded = jwt.decode(
        token,
        settings.security.secret_key,
        algorithms=[settings.security.algorithm],
        audience=settings.security.jwt_audience,
    )
    assert decoded["sub"] == str(uid)
    assert decoded["type"] == TokenType.CLIENT
    assert decoded["iss"] == settings.security.jwt_issuer


def test_verify_websocket_access_token_accepts_ws_type():
    uid = uuid.uuid4()
    token = create_access_token(uid, TokenType.WEBSOCKET)
    sub = verify_websocket_access_token(token)
    assert sub == str(uid)


def test_verify_websocket_access_token_rejects_wrong_type():
    uid = uuid.uuid4()
    token = create_access_token(uid, TokenType.CLIENT)
    with pytest.raises(Exception):
        verify_websocket_access_token(token)


def test_hash_and_verify_jti_roundtrip():
    jti = "random-jti"
    h = hash_jti(jti)
    assert verify_jti(jti, h)
    assert not verify_jti(jti + "x", h)

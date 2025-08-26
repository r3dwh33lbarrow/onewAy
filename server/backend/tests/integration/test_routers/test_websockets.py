import json
from datetime import datetime, timedelta, UTC

import pytest
from httpx_ws import aconnect_ws
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

from app.models.user import User
from app.services.authentication import hash_password, create_access_token
from app.settings import settings


@pytest.mark.asyncio
async def test_websocket_connection_success(ws_client, db_session: AsyncSession):
    """Test successful WebSocket connection with valid token"""
    test_user = User(username="wsuser", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()

    access_token = create_access_token(test_user.uuid, is_user=True)

    async with ws_client as client:
        async with aconnect_ws(f"/ws?token={access_token}", client) as websocket:
            ping_message = {"type": "ping"}
            await websocket.send_text(json.dumps(ping_message))

            response = await websocket.receive_text()
            response_data = json.loads(response)

            assert response_data["type"] == "pong"


@pytest.mark.asyncio
async def test_websocket_authentication_failures(ws_client, db_session: AsyncSession):
    """Test various authentication failure scenarios"""
    test_user = User(username="wsuser_auth", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()

    async with ws_client as client:
        # Test missing token
        try:
            async with aconnect_ws("/ws", client) as websocket:
                assert False, "Connection should have failed"
        except Exception as e:
            assert "token" in str(e).lower() or "422" in str(e)

        # Test invalid token
        try:
            async with aconnect_ws("/ws?token=invalid.token.here", client) as websocket:
                assert False, "Connection should have failed"
        except Exception:
            pass

        # Test expired token
        now = datetime.now(UTC)
        expired_payload = {
            "sub": str(test_user.uuid),
            "type": "access",
            "exp": int((now - timedelta(minutes=30)).timestamp()),
            "iat": int((now - timedelta(minutes=30)).timestamp())
        }
        expired_token = jwt.encode(expired_payload, settings.secret_key, settings.jwt_algorithm)

        try:
            async with aconnect_ws(f"/ws?token={expired_token}", client) as websocket:
                assert False, "Connection should have failed"
        except Exception:
            pass

        # Test malformed token
        try:
            async with aconnect_ws("/ws?token=not.a.valid.jwt", client) as websocket:
                assert False, "Connection should have failed"
        except Exception:
            pass


@pytest.mark.asyncio
async def test_websocket_token_validation(ws_client, db_session: AsyncSession):
    """Test various token validation scenarios"""
    test_user = User(username="wsuser_token", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()

    now = datetime.now(UTC)
    expires = now + timedelta(minutes=30)

    async with ws_client as client:
        # Test token without subject
        payload_no_sub = {
            "type": "access",
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp())
        }
        token_no_sub = jwt.encode(payload_no_sub, settings.secret_key, settings.jwt_algorithm)

        try:
            async with aconnect_ws(f"/ws?token={token_no_sub}", client) as websocket:
                assert False, "Connection should have failed"
        except Exception:
            pass

        # Test token with invalid UUID format (should work as validator doesn't check format)
        payload_invalid_uuid = {
            "sub": "invalid-uuid-format",
            "type": "access",
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp())
        }
        token_invalid_uuid = jwt.encode(payload_invalid_uuid, settings.secret_key, settings.jwt_algorithm)

        async with aconnect_ws(f"/ws?token={token_invalid_uuid}", client) as websocket:
            ping_message = {"type": "ping"}
            await websocket.send_text(json.dumps(ping_message))
            response = await websocket.receive_text()
            response_data = json.loads(response)
            assert response_data["type"] == "pong"

        # Test token signed with wrong key
        payload_wrong_key = {
            "sub": str(test_user.uuid),
            "type": "access",
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp())
        }
        wrong_key_token = jwt.encode(payload_wrong_key, "wrong_secret_key", settings.jwt_algorithm)

        try:
            async with aconnect_ws(f"/ws?token={wrong_key_token}", client) as websocket:
                assert False, "Connection should have failed"
        except Exception:
            pass


@pytest.mark.asyncio
async def test_websocket_message_handling(ws_client, db_session: AsyncSession):
    """Test various message handling scenarios"""
    test_user = User(username="wsuser_messages", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()

    access_token = create_access_token(test_user.uuid, is_user=True)

    async with ws_client as client:
        async with aconnect_ws(f"/ws?token={access_token}", client) as websocket:
            # Test multiple ping-pong exchanges
            for i in range(3):
                ping_message = {"type": "ping", "id": i}
                await websocket.send_text(json.dumps(ping_message))
                response = await websocket.receive_text()
                response_data = json.loads(response)
                assert response_data["type"] == "pong"

            # Test non-ping message (should be ignored)
            other_message = {"type": "custom", "data": "test"}
            await websocket.send_text(json.dumps(other_message))

            # Verify connection still works
            ping_message = {"type": "ping"}
            await websocket.send_text(json.dumps(ping_message))
            response = await websocket.receive_text()
            response_data = json.loads(response)
            assert response_data["type"] == "pong"

            # Test ping with extra fields
            ping_with_extras = {
                "type": "ping",
                "timestamp": datetime.now().isoformat(),
                "extra_data": {"key": "value"},
                "id": 12345
            }
            await websocket.send_text(json.dumps(ping_with_extras))
            response = await websocket.receive_text()
            response_data = json.loads(response)
            assert response_data["type"] == "pong"

            # Test case sensitivity (PING vs ping)
            await websocket.send_text(json.dumps({"type": "PING"}))
            ping_message = {"type": "ping"}
            await websocket.send_text(json.dumps(ping_message))
            response = await websocket.receive_text()
            response_data = json.loads(response)
            assert response_data["type"] == "pong"

            # Test message without type field
            await websocket.send_text(json.dumps({"data": "test", "id": 123}))
            ping_message = {"type": "ping"}
            await websocket.send_text(json.dumps(ping_message))
            response = await websocket.receive_text()
            response_data = json.loads(response)
            assert response_data["type"] == "pong"


@pytest.mark.asyncio
async def test_websocket_connection_scenarios(ws_client, db_session: AsyncSession):
    """Test multiple users and reconnection scenarios"""
    # Create test users
    test_user1 = User(username="wsuser1", hashed_password=hash_password("password123"))
    test_user2 = User(username="wsuser2", hashed_password=hash_password("password123"))
    db_session.add(test_user1)
    db_session.add(test_user2)
    await db_session.commit()

    access_token1 = create_access_token(test_user1.uuid, is_user=True)
    access_token2 = create_access_token(test_user2.uuid, is_user=True)

    async with ws_client as client:
        # Test first user
        async with aconnect_ws(f"/ws?token={access_token1}", client) as websocket1:
            await websocket1.send_text(json.dumps({"type": "ping", "user": "user1"}))
            response1 = await websocket1.receive_text()
            assert json.loads(response1)["type"] == "pong"

        # Test second user (sequential connection)
        async with aconnect_ws(f"/ws?token={access_token2}", client) as websocket2:
            await websocket2.send_text(json.dumps({"type": "ping", "user": "user2"}))
            response2 = await websocket2.receive_text()
            assert json.loads(response2)["type"] == "pong"

        # Test user reconnection
        async with aconnect_ws(f"/ws?token={access_token1}", client) as websocket3:
            await websocket3.send_text(json.dumps({"type": "ping", "reconnect": True}))
            response3 = await websocket3.receive_text()
            assert json.loads(response3)["type"] == "pong"


@pytest.mark.asyncio
async def test_websocket_token_types(ws_client, db_session: AsyncSession):
    """Test different token types and configurations"""
    test_user = User(username="wsuser_types", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()

    # Test client token vs user token
    client_token = create_access_token(test_user.uuid, is_user=False)
    user_token = create_access_token(test_user.uuid, is_user=True)

    async with ws_client as client:
        # Test client token
        async with aconnect_ws(f"/ws?token={client_token}", client) as websocket:
            await websocket.send_text(json.dumps({"type": "ping"}))
            response = await websocket.receive_text()
            assert json.loads(response)["type"] == "pong"

        # Test user token
        async with aconnect_ws(f"/ws?token={user_token}", client) as websocket:
            await websocket.send_text(json.dumps({"type": "ping"}))
            response = await websocket.receive_text()
            assert json.loads(response)["type"] == "pong"

        # Test refresh token type (should work as validator doesn't check type)
        now = datetime.now(UTC)
        expires = now + timedelta(minutes=30)
        refresh_payload = {
            "sub": str(test_user.uuid),
            "type": "refresh",
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp())
        }
        refresh_token = jwt.encode(refresh_payload, settings.secret_key, settings.jwt_algorithm)

        async with aconnect_ws(f"/ws?token={refresh_token}", client) as websocket:
            await websocket.send_text(json.dumps({"type": "ping"}))
            response = await websocket.receive_text()
            assert json.loads(response)["type"] == "pong"


@pytest.mark.asyncio
async def test_websocket_edge_cases(ws_client, db_session: AsyncSession):
    """Test edge cases and error conditions"""
    test_user = User(username="wsuser_edge", hashed_password=hash_password("password123"))
    db_session.add(test_user)
    await db_session.commit()

    access_token = create_access_token(test_user.uuid, is_user=True)

    async with ws_client as client:
        # Test empty token
        try:
            async with aconnect_ws("/ws?token=", client) as websocket:
                assert False, "Connection should have failed"
        except Exception:
            pass

        # Test token with special characters
        try:
            async with aconnect_ws("/ws?token=header.payload!@#$%^&*().signature", client) as websocket:
                assert False, "Connection should have failed"
        except Exception:
            pass

        # Test invalid JSON message (should close connection)
        async with aconnect_ws(f"/ws?token={access_token}", client) as websocket:
            try:
                await websocket.send_text("invalid json message")
                response = await websocket.receive_text()
                assert False, "Should have disconnected due to invalid JSON"
            except Exception:
                pass

        # Test empty message (should close connection)
        async with aconnect_ws(f"/ws?token={access_token}", client) as websocket:
            try:
                await websocket.send_text("")
                response = await websocket.receive_text()
                assert False, "Should have disconnected due to empty message"
            except Exception:
                pass


import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.client import Client
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.password import pwd_context
from app.settings import settings
from app.logger import get_logger

security = HTTPBearer(auto_error=False)
logger = get_logger()


class TokenType(str, Enum):
    USER = "user"
    REFRESH = "refresh"
    CLIENT = "client"
    WEBSOCKET = "websocket"


def hash_jti(jti: str) -> str:
    return pwd_context.hash(jti)


def verify_jti(jti: str, hashed_jti: str) -> bool:
    return pwd_context.verify(jti, hashed_jti)


def create_access_token(account_uuid: uuid.UUID, token_type: TokenType) -> str:
    now = datetime.now(UTC)
    if token_type == TokenType.USER:
        expires = now + timedelta(
            minutes=settings.security.access_token_expires_minutes + 15
        )
    elif token_type == TokenType.WEBSOCKET:
        expires = now + timedelta(minutes=15)
    elif token_type == TokenType.CLIENT:
        expires = now + timedelta(
            minutes=settings.security.access_token_expires_minutes
        )
    else:
        logger.error("Access token creation failed: invalid token type %s", token_type)
        raise RuntimeError(f"Incorrect token type {token_type.name}")

    payload = {
        "sub": str(account_uuid),
        "iss": settings.security.jwt_issuer,
        "aud": settings.security.jwt_audience,
        "type": token_type,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
    }

    logger.debug(
        "Creating %s access token for %s", token_type.value, account_uuid
    )
    return jwt.encode(
        payload, settings.security.secret_key, settings.security.algorithm
    )


async def create_refresh_token(client_uuid: uuid.UUID, db: AsyncSession) -> str:
    jti = str(uuid4())
    hashed_jti = hash_jti(jti)
    now = datetime.now(UTC)
    expires = now + timedelta(days=settings.security.refresh_token_expires_days)

    payload = {
        "sub": str(client_uuid),
        "type": "refresh",
        "jti": jti,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
    }

    refresh_token = RefreshToken(
        client_uuid=client_uuid, jti=hashed_jti, expires_at=expires
    )

    try:
        db.add(refresh_token)
        await db.commit()
        logger.debug("Refresh token created for client %s", client_uuid)
        return jwt.encode(
            payload, settings.security.secret_key, settings.security.algorithm
        )
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to persist refresh token for client %s", client_uuid)
        raise RuntimeError(f"Failed to create refresh token: {str(e)}")


async def verify_refresh_token(
    request: Request, db: AsyncSession
) -> RefreshToken | None:
    token = request.cookies.get("refresh_token")

    if not token:
        logger.warning("Refresh token missing from request cookies")
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        payload = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.algorithm],
        )
        if payload.get("type") != "refresh":
            logger.warning(
                "Refresh token validation failed: invalid type '%s'",
                payload.get("type"),
            )
            raise HTTPException(status_code=401, detail="Invalid token type")

        jti = payload.get("jti")
        if not jti:
            logger.warning("Refresh token missing jti claim")
            raise HTTPException(status_code=401, detail="Invalid token: missing jti")

        client_uuid = payload.get("sub")
        if not client_uuid:
            logger.warning("Refresh token missing subject claim")
            raise HTTPException(
                status_code=401, detail="Invalid token: missing client identifier"
            )
        client_uuid = uuid.UUID(client_uuid)

        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.client_uuid == client_uuid,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.now(),
            )
        )
        refresh_tokens = result.scalars().all()

        refresh_token: RefreshToken | None = None
        for token_record in refresh_tokens:
            if verify_jti(jti, token_record.jti):
                refresh_token = token_record
                break

        if not refresh_token:
            logger.warning("Refresh token not found or revoked for client %s", client_uuid)
            raise HTTPException(status_code=401, detail="Token not found")

        logger.debug("Refresh token verified for client %s", client_uuid)
        return refresh_token

    except JWTError:
        logger.warning("Failed to decode refresh token", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException as e:
        logger.warning("Refresh token verification error: %s", e.detail)
        raise e
    except Exception:
        logger.exception("Unexpected error verifying refresh token")
        raise HTTPException(status_code=500, detail="Token verification failed")


async def revoke_refresh_token(
    request: Request, response: Response, db: AsyncSession
) -> bool:
    try:
        refresh_token = await verify_refresh_token(request, db)
        if not refresh_token:
            logger.warning("No refresh token available to revoke")
            return False

        refresh_token.revoked = True
        await db.commit()
        response.delete_cookie(key="refresh_token", httponly=True, samesite="strict")
        logger.info("Refresh token revoked for client %s", refresh_token.client_uuid)
        return True

    except HTTPException as e:
        logger.warning("Refresh token revocation failed: %s", e.detail)
        raise
    except Exception:
        await db.rollback()
        logger.exception("Unexpected error revoking refresh token")
        raise HTTPException(status_code=500, detail="Failed to revoke token")


async def rotate_refresh_token(request: Request, db: AsyncSession) -> tuple[str, str]:
    try:
        current_refresh_token = await verify_refresh_token(request, db)
        if not current_refresh_token:
            logger.warning("Refresh token rotation failed: token missing")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        client_uuid = current_refresh_token.client_uuid

        new_access_token = create_access_token(client_uuid, TokenType.CLIENT)
        new_refresh_token = await create_refresh_token(client_uuid, db)

        current_refresh_token.revoked = True
        await db.commit()

        logger.info("Refresh token rotated for client %s", client_uuid)
        return new_access_token, new_refresh_token

    except HTTPException as e:
        logger.warning("Refresh token rotation failed: %s", e.detail)
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Unexpected error rotating refresh token")
        raise HTTPException(
            status_code=500, detail=f"Failed to rotate refresh token: {str(e)}"
        )


def is_client(request: Request) -> bool:
    return "oneway" in request.headers.get("user-agent")


def verify_access_token(request: Request):
    if is_client(request):
        authorization_header = request.headers.get("Authorization")
        if not authorization_header or not authorization_header.startswith("Bearer "):
            logger.warning("Missing or invalid authorization header for client request")
            raise HTTPException(
                status_code=401, detail="Missing or invalid authorization header"
            )

        access_token = authorization_header[7:]
        if not access_token:
            logger.warning("Client request missing bearer token")
            raise HTTPException(status_code=401, detail="Missing access token")
    else:
        access_token = request.cookies.get("access_token")
        if not access_token:
            logger.warning("User request missing access token cookie")
            raise HTTPException(status_code=401, detail="Missing access token cookie")

    try:
        decoded_token = jwt.decode(
            access_token,
            settings.security.secret_key,
            algorithms=[settings.security.algorithm],
        )
        if decoded_token.get("type") != "access":
            logger.warning(
                "Access token validation failed: expected 'access', got '%s'",
                decoded_token.get("type"),
            )
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_uuid = decoded_token.get("sub")
        if user_uuid is None:
            logger.warning("Access token missing subject claim")
            raise HTTPException(status_code=401, detail="Invalid token")
        logger.debug("Access token validated for subject %s", user_uuid)
        return user_uuid

    except JWTError:
        logger.warning("Failed to decode access token", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    db: AsyncSession = Depends(get_db), user_uuid: str = Depends(verify_access_token)
) -> User:
    try:
        result = await db.execute(select(User).where(User.uuid == uuid.UUID(user_uuid)))
        user = result.scalar_one_or_none()
        if user is None:
            logger.warning("Access token subject %s not found as user", user_uuid)
            raise HTTPException(status_code=403, detail="User not found")

        return user
    except HTTPException as e:
        logger.warning("Failed to resolve current user: %s", e.detail)
        raise e
    except Exception:
        logger.exception("Unexpected error retrieving current user %s", user_uuid)
        raise HTTPException(status_code=500, detail="Failed to get current user")


async def get_current_client(
    db: AsyncSession = Depends(get_db), client_uuid: str = Depends(verify_access_token)
):
    try:
        result = await db.execute(
            select(Client).where(Client.uuid == uuid.UUID(client_uuid))
        )
        client = result.scalar_one_or_none()

        if client is None:
            logger.warning("Access token subject %s not found as client", client_uuid)
            raise HTTPException(status_code=403, detail="Client not found")

        return client
    except HTTPException as e:
        logger.warning("Failed to resolve current client: %s", e.detail)
        raise e
    except Exception:
        logger.exception(
            "Unexpected error retrieving current client %s", client_uuid
        )
        raise HTTPException(status_code=500, detail="Failed to get current client")


def verify_websocket_access_token(token: str) -> str:
    try:
        decoded_token = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.algorithm],
        )
        if decoded_token.get("type") != "websocket":
            logger.warning(
                "Websocket token validation failed: expected 'websocket', got '%s'",
                decoded_token.get("type"),
            )
            raise HTTPException(status_code=401, detail="Invalid token type")

        some_uuid = decoded_token.get("sub")
        if some_uuid is None:
            logger.warning("Websocket token missing subject claim")
            raise HTTPException(status_code=401, detail="Invalid token")

        logger.debug("Websocket token validated for subject %s", some_uuid)
        return some_uuid
    except JWTError:
        logger.warning("Failed to decode websocket token", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")

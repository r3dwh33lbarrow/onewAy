import os
import uuid
from datetime import timedelta, datetime, UTC
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken

ACCESS_TOKEN_EXPIRE_MINUTES = 15
ALGORITHM = "HS256"
REFRESH_TOKEN_EXPIRE_DAYS = 7
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")

security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["scrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using scrypt hashing algorithm.

    Args:
        password: The plaintext password to be hashed

    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def hash_jti(jti: str) -> str:
    """
    Hash a JTI (JSON Web Token ID) using scrypt hashing algorithm.

    This provides additional security by ensuring that even if the database
    is compromised, the stored JTIs cannot be directly used.

    Args:
        jti: The plaintext JTI to be hashed

    Returns:
        str: The hashed JTI
    """
    return pwd_context.hash(jti)


def verify_jti(jti: str, hashed_jti: str) -> bool:
    """
    Verify a JTI against its hashed version.

    Args:
        jti: The plaintext JTI to verify
        hashed_jti: The hashed JTI to compare against

    Returns:
        bool: True if the JTI matches the hash, False otherwise
    """
    return pwd_context.verify(jti, hashed_jti)


def create_access_token(user_or_client_uuid: uuid.UUID) -> str:
    """
    Create a new access token for a user or client.

    This function generates a JSON Web Token (JWT) that includes the user's or client's UUID,
    the token type, the expiration time, and the issued-at time. The token is signed using
    the HS256 algorithm and a secret key.

    Args:
        user_or_client_uuid (uuid.UUID): The UUID of the user or client for whom the access token is being created.

    Returns:
        str: The encoded JWT access token.
    """
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_or_client_uuid),
        "type": "access",
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp())
    }

    return jwt.encode(payload, SECRET_KEY, ALGORITHM)


async def create_refresh_token(client_uuid: uuid.UUID, db: AsyncSession) -> str:
    """
    Create a new refresh token for a client.

    This function generates a JSON Web Token (JWT) with a payload containing the client's UUID,
    token type, a unique identifier (jti), expiration time, and issued-at time. The token is
    stored in the database for future validation with the JTI hashed for security.

    Args:
        client_uuid (uuid.UUID): The UUID of the client for whom the refresh token is being created.
        db (AsyncSession): The database session used to store the refresh token.

    Returns:
        str: The encoded JWT refresh token.

    Raises:
        RuntimeError: If the database operation to store the refresh token fails.
    """
    jti = str(uuid4())
    hashed_jti = hash_jti(jti)  # Hash the JTI for secure storage
    now = datetime.now(UTC)
    expires = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(client_uuid),
        "type": "refresh",
        "jti": jti,  # Store plaintext JTI in the JWT payload
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp())
    }

    refresh_token = RefreshToken(
        client_uuid=client_uuid,
        jti=hashed_jti,  # Store hashed JTI in the database
        expires_at=expires
    )

    try:
        db.add(refresh_token)
        await db.commit()
        return jwt.encode(payload, SECRET_KEY, ALGORITHM)
    except Exception as e:
        await db.rollback()
        raise RuntimeError(f"Failed to create refresh token: {str(e)}")


async def verify_refresh_token(token: str, db: AsyncSession) -> Optional[RefreshToken]:
    """
    Verify the validity of a refresh token.

    This function decodes a JSON Web Token (JWT) and validates its type, unique identifier (jti),
    and expiration time. It also checks the database to ensure the token exists, has not been revoked,
    and has not expired. The JTI is verified against the hashed version stored in the database.

    Args:
        token (str): The encoded JWT refresh token to be verified.
        db (AsyncSession): The database session used to query the refresh token.

    Returns:
        Optional[RefreshToken]: The corresponding RefreshToken object if the token is valid,
        or None if the token is invalid.

    Raises:
        HTTPException: If the token is invalid, revoked, expired, or not found in the database.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Invalid token: missing jti")

        # Query active refresh tokens that haven't expired or been revoked
        # We'll need to check the JTI hash for each one, but we can limit the search
        result = await db.execute(
            Select(RefreshToken).where(
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.now(UTC)
            )
        )
        refresh_tokens = result.scalars().all()

        refresh_token: Optional[RefreshToken] = None
        for token_record in refresh_tokens:
            if verify_jti(jti, token_record.jti):
                refresh_token = token_record
                break

        if not refresh_token:
            raise HTTPException(status_code=401, detail="Token not found")

        return refresh_token

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=500, detail="Token verification failed")


async def revoke_refresh_token(token: str, db: AsyncSession) -> bool:
    """
    Revoke a refresh token.

    This function marks a refresh token as revoked in the database, preventing it from being used
    for future authentication. It first verifies the validity of the token and then updates its
    status in the database.

    Args:
        token (str): The encoded JWT refresh token to be revoked.
        db (AsyncSession): The database session used to update the refresh token.

    Returns:
        bool: True if the token was successfully revoked, False if the token is invalid.

    Raises:
        HTTPException: If the token verification or revocation process fails.
    """
    try:
        refresh_token = await verify_refresh_token(token, db)
        if not refresh_token:
            return False

        refresh_token.revoked = True
        await db.commit()
        return True

    except HTTPException:
        raise

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to revoke token")


async def rotate_refresh_token(token: str, db: AsyncSession) -> tuple[str, str]:
    """
    Rotate a refresh token by creating new access and refresh tokens and revoking the old refresh token.

    This implements refresh token rotation for replay attack protection. Once a refresh token is used,
    it's immediately revoked and replaced with a new one, limiting the window of vulnerability if
    a token is compromised.

    Args:
        token (str): The current refresh token to be rotated.
        db (AsyncSession): The database session used for token operations.

    Returns:
        tuple[str, str]: A tuple containing (new_access_token, new_refresh_token).

    Raises:
        HTTPException: If the current token is invalid, expired, or revoked, or if rotation fails.
    """
    try:
        current_refresh_token = await verify_refresh_token(token, db)
        if not current_refresh_token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        client_uuid = current_refresh_token.client_uuid

        new_access_token = create_access_token(client_uuid)
        new_refresh_token = await create_refresh_token(client_uuid, db)

        current_refresh_token.revoked = True
        await db.commit()

        return new_access_token, new_refresh_token

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to rotate refresh token: {str(e)}")

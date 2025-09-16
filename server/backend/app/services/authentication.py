import uuid
from datetime import timedelta, datetime, UTC
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, Request, Depends, Response
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.client import Client
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.password import pwd_context
from app.settings import settings

ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
ALGORITHM = settings.jwt_algorithm
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days
SECRET_KEY = settings.secret_key

security = HTTPBearer(auto_error=False)


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


def create_access_token(user_or_client_uuid: uuid.UUID, is_user: bool = False, is_ws: bool = False) -> str:
    """
    Create a new access token for a user or client.

    This function generates a JSON Web Token (JWT) that includes the user's or client's UUID,
    the token type, the expiration time, and the issued-at time. The token is signed using
    the HS256 algorithm and a secret key.

    Args:
        user_or_client_uuid (uuid.UUID): The UUID of the user or client for whom the access token is being created.
        is_user (bool, optional): Indicates whether the token is for a user or client. Defaults to False.

    Returns:
        str: The encoded JWT access token.
    """
    now = datetime.now(UTC)
    # Extend token expiration time for user accounts
    if is_user:
        expires = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES + 15)
    elif is_ws:
        expires = now + timedelta(minutes=15)
    else:
        expires = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    token_type = "websocket" if is_ws else "access"
    payload = {
        "sub": str(user_or_client_uuid),
        "type": token_type,
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
    hashed_jti = hash_jti(jti)
    now = datetime.now(UTC)
    expires = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(client_uuid),
        "type": "refresh",
        "jti": jti,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp())
    }

    refresh_token = RefreshToken(
        client_uuid=client_uuid,
        jti=hashed_jti,
        expires_at=expires.replace(tzinfo=None)
    )

    try:
        db.add(refresh_token)
        await db.commit()
        return jwt.encode(payload, SECRET_KEY, ALGORITHM)
    except Exception as e:
        await db.rollback()
        raise RuntimeError(f"Failed to create refresh token: {str(e)}")


async def verify_refresh_token(request: Request, db: AsyncSession) -> Optional[RefreshToken]:
    """
    Verify the validity of a refresh token from request cookies.

    This function extracts a refresh token from the request cookies, decodes the JSON Web Token (JWT)
    and validates its type, unique identifier (jti), and expiration time. It also checks the database
    to ensure the token exists, has not been revoked, and has not expired. The JTI is verified against
    the hashed version stored in the database.

    Args:
        request (Request): The HTTP request object containing the cookies.
        db (AsyncSession): The database session used to query the refresh token.

    Returns:
        RefreshToken: The corresponding RefreshToken object if the token is valid.

    Raises:
        HTTPException: If the token is missing, invalid, revoked, expired, or not found in the database.
    """
    token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Invalid token: missing jti")

        client_uuid = payload.get("sub")
        if not client_uuid:
            raise HTTPException(status_code=401,
                                detail="Invalid token: missing client identifier")
        client_uuid = uuid.UUID(client_uuid)

        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.client_uuid == client_uuid,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.now().replace(tzinfo=None)
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
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=500, detail="Token verification failed")


async def revoke_refresh_token(request: Request, response: Response, db: AsyncSession) -> bool:
    """
    Revoke a refresh token and remove the refresh token cookie.

    This function marks a refresh token as revoked in the database, preventing it from being used
    for future authentication. It first verifies the validity of the token from the request cookies,
    updates its status in the database, and then removes the refresh token cookie from the client.

    Args:
        request (Request): The HTTP request object containing the refresh token cookie.
        response (Response): The HTTP response object used to remove the cookie.
        db (AsyncSession): The database session used to update the refresh token.

    Returns:
        bool: True if the token was successfully revoked, False if the token is invalid.

    Raises:
        HTTPException: If the token verification or revocation process fails.
    """
    try:
        refresh_token = await verify_refresh_token(request, db)
        if not refresh_token:
            return False

        refresh_token.revoked = True
        await db.commit()

        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            samesite="strict"
        )

        return True

    except HTTPException:
        raise

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to revoke token")


async def rotate_refresh_token(request: Request, db: AsyncSession) -> tuple[str, str]:
    """
    Rotate a refresh token by creating new access and refresh tokens and revoking the old refresh token.

    This implements refresh token rotation for replay attack protection. Once a refresh token is used,
    it's immediately revoked and replaced with a new one, limiting the window of vulnerability if
    a token is compromised. The refresh token is extracted from the request cookies.

    Args:
        request (Request): The HTTP request object containing the refresh token cookie.
        db (AsyncSession): The database session used for token operations.

    Returns:
        tuple[str, str]: A tuple containing (new_access_token, new_refresh_token).

    Raises:
        HTTPException: If the current token is invalid, expired, or revoked, or if rotation fails.
    """
    try:
        current_refresh_token = await verify_refresh_token(request, db)
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


def is_client(request: Request) -> bool:
    return "oneway" in request.headers.get("user-agent")


def verify_access_token(request: Request):
    """
    Verify the validity of an access token provided in the request headers.

    This function checks for the presence of an access token in the request's
    Authorization header (Bearer token format). It decodes the token using the
    configured secret key and algorithm, and extracts the user UUID from the
    token payload. If the token is missing, invalid, or does not contain a
    valid user UUID, an HTTPException is raised.

    Args:
        request (Request): The HTTP request object containing the headers.

    Returns:
        str: The UUID of the user extracted from the access token.

    Raises:
        HTTPException: If the access token is missing, invalid, or does not contain a valid user UUID.
    """
    if is_client(request):
        authorization_header = request.headers.get("Authorization")

        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

        access_token = authorization_header[7:]

        if not access_token:
            raise HTTPException(status_code=401, detail="Missing access token")

    else:
        access_token = request.cookies.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="Missing access token cookie")

    try:
        decoded_token = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_uuid = decoded_token.get("sub")

        if user_uuid is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return user_uuid

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
        db: AsyncSession = Depends(get_db),
        user_uuid: str = Depends(verify_access_token)
) -> User:
    """
    Retrieve the current authenticated user from the database.

    This function uses the user UUID extracted from the access token to query the database
    and fetch the corresponding user record. If the user is not found or an error occurs
    during the database query, an HTTPException is raised.

    Args:
        db (AsyncSession): The database session used to query the user.
        user_uuid (str): The UUID of the user extracted from the access token.

    Returns:
        User: The user object corresponding to the authenticated user.

    Raises:
        HTTPException:
            - 404 Not Found: If the user does not exist in the database.
            - 500 Internal Server Error: If there is an error during the database query.
    """
    try:
        result = await db.execute(select(User).where(User.uuid == uuid.UUID(user_uuid)))
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=403,
                detail="User not found"
            )

        return user
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to get current user"
        )


async def get_current_client(db: AsyncSession = Depends(get_db), client_uuid: str = Depends(verify_access_token)):
    try:
        result = await db.execute(select(Client).where(Client.uuid == uuid.UUID(client_uuid)))
        client = result.scalar_one_or_none()

        if client is None:
            raise HTTPException(
                status_code=403,
                detail="Client not found"
            )

        return client
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to get current client"
        )


def verify_websocket_access_token(token: str) -> str:
    """
    Verify access token for WebSocket connections.

    Args:
        token: The access token to verify

    Returns:
        str: The user UUID if token is valid

    Raises:
        HTTPException: If token is invalid
    """
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        some_uuid = decoded_token.get("sub")

        if some_uuid is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return some_uuid

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

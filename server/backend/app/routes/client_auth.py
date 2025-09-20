from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.logger import get_logger
from app.models.client import Client
from app.schemas.client_auth import *
from app.schemas.general import BasicTaskResponse, TokenResponse
from app.services.authentication import (
    create_access_token,
    create_refresh_token,
    rotate_refresh_token,
    TokenType,
)
from app.services.password import hash_password

router = APIRouter(prefix="/client/auth")
logger = get_logger()


@router.post("/enroll", response_model=BasicTaskResponse)
async def client_auth_enroll(
    enroll_request: ClientEnrollRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new client in the system.

    Args:
        enroll_request: Client registration data including username, password, and version
        request: HTTP request object containing client IP address
        db: Database session for executing queries

    Returns:
        Success confirmation upon successful registration

    Raises:
        HTTPException: 409 if username already exists, 500 if database error occurs
    """
    logger.debug("Client enrollment attempt for '%s'", enroll_request.username)

    existing_client = await db.execute(
        select(Client).where(Client.username == enroll_request.username)
    )
    if existing_client.scalar_one_or_none():
        logger.warning(
            "Client enrollment failed: username '%s' already exists",
            enroll_request.username,
        )
        raise HTTPException(status_code=409, detail="Username already exists")

    new_client = Client(
        username=enroll_request.username,
        hashed_password=hash_password(enroll_request.password),
        ip_address=request.client.host,
        client_version=enroll_request.client_version,
    )

    try:
        db.add(new_client)
        await db.commit()
        logger.info("Client '%s' enrolled", new_client.username)
        return {"result": "success"}

    except Exception:
        await db.rollback()
        logger.exception("Failed to enroll client '%s'", enroll_request.username)
        raise HTTPException(
            status_code=500, detail="Failed to add client to the database"
        )


@router.post("/login", response_model=TokenResponse)
async def client_auth_login(
    login_request: ClientLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a client and provide access tokens.

    Args:
        login_request: Client credentials (username and password)
        request: HTTP request object containing client IP address
        response: HTTP response object for setting cookies
        db: Database session for executing queries

    Returns:
        Access token and token type for authenticated requests

    Raises:
        HTTPException: 401 if credentials invalid, 500 if database error occurs

    Note:
        Sets refresh token as httpOnly cookie and updates client status to alive
    """
    logger.debug(
        "Client login attempt for '%s' from %s",
        login_request.username,
        request.client.host if request.client else "unknown",
    )

    client = await db.execute(
        select(Client).where(Client.username == login_request.username)
    )
    client = client.scalar_one_or_none()

    if not client or not client.verify_password(login_request.password):
        logger.warning("Invalid credentials for client '%s'", login_request.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    client.ip_address = request.client.host
    client.alive = True

    try:
        access_token = create_access_token(client.uuid, TokenType.CLIENT)
        refresh_token = await create_refresh_token(client.uuid, db)
        await db.commit()

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
        )

        logger.info(
            "Client '%s' logged in from %s",
            client.username,
            request.client.host if request.client else "unknown",
        )
        return {"access_token": access_token, "token_type": "Bearer"}
    except HTTPException as e:
        raise e
    except Exception:
        await db.rollback()
        logger.exception("Login failure for client '%s'", login_request.username)
        raise HTTPException(
            status_code=500, detail="Login failed due to database error"
        )


@router.post("/refresh", response_model=TokenResponse)
async def client_auth_refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """
    Refresh client access token using refresh token from cookies.

    Args:
        request: HTTP request object containing refresh token cookie
        response: HTTP response object for setting new cookie
        db: Database session for executing queries

    Returns:
        New access token and token type

    Raises:
        HTTPException: 401 if refresh token invalid, 500 if database error occurs

    Note:
        Rotates refresh token and updates cookie with new value
    """
    try:
        new_access_token, new_refresh_token = await rotate_refresh_token(request, db)
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
        )

        logger.info("Rotated client refresh token")
        return {"access_token": new_access_token, "token_type": "Bearer"}

    except HTTPException as e:
        raise e
    except Exception:
        await db.rollback()
        logger.exception("Failed to refresh client access token")
        raise HTTPException(
            status_code=500, detail="Token refresh failed due to database error"
        )

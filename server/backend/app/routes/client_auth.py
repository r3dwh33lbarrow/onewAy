from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.client import Client
from app.schemas.client_auth import ClientEnrollRequest, ClientLoginRequest
from app.schemas.general import BasicTaskResponse, TokenResponse
from app.services.authentication import create_access_token, create_refresh_token, rotate_refresh_token, \
    verify_refresh_token
from app.services.password import hash_password

router = APIRouter(prefix="/client/auth")


@router.post("/enroll", response_model=BasicTaskResponse)
async def client_auth_enroll(enroll_request: ClientEnrollRequest,
                             request: Request, db: AsyncSession = Depends(get_db)):
    """
    Enroll a new client by creating an account in the database.

    This endpoint checks if the username already exists, and if not, creates a new
    client account with the provided username, password, and client version. The
    client's IP address is also recorded.

    Args:
        enroll_request (ClientEnrollRequest): The enrollment request containing the username, password, and client version.
        request (Request): The FastAPI request object, used to retrieve the client's IP address.
        db (AsyncSession): The database session dependency.

    Returns:
        BasicTaskResponse: A response indicating the success of the enrollment.

    Raises:
        HTTPException: If the username already exists or if a database error occurs.
    """
    existing_client = await db.execute(select(Client).where(Client.username == enroll_request.username))
    if existing_client.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    new_client = Client(
        username=enroll_request.username,
        hashed_password=hash_password(enroll_request.password),
        ip_address=request.client.host,
        client_version=enroll_request.client_version
    )

    try:
        db.add(new_client)
        await db.commit()
        return {"result": "success"}

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500,
                            detail="Failed to add client to the database")


@router.post("/login", response_model=TokenResponse)
async def client_auth_login(login_request: ClientLoginRequest, request: Request,
                            response: Response, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a client and issue access and refresh tokens.

    This endpoint verifies the provided username and password, updates the client's
    IP address and status, and generates a new access token and refresh token. The
    refresh token is stored as an HTTP-only cookie.

    Args:
        login_request (ClientLoginRequest): The login request containing the username and password.
        request (Request): The FastAPI request object, used to retrieve the client's IP address.
        response (Response): The FastAPI response object, used to set the refresh token cookie.
        db (AsyncSession): The database session dependency.

    Returns:
        TokenResponse: A response containing the access token and its type.

    Raises:
        HTTPException: If the username or password is invalid, or if a database error occurs.
    """
    client = await db.execute(select(Client).where(Client.username == login_request.username))
    client = client.scalar_one_or_none()

    if not client or not client.verify_password(login_request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    client.ip_address = request.client.host
    client.alive = True

    try:
        access_token = create_access_token(client.uuid)
        refresh_token = await create_refresh_token(client.uuid, db)
        await db.commit()

        response.set_cookie(key="refresh_token", value=refresh_token,
                            httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)

        return {"access_token": access_token, "token_type": "Bearer"}
    except HTTPException as e:
        raise e
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500,
                            detail="Login failed due to database error")


@router.post("/refresh", response_model=TokenResponse)
async def client_auth_refresh(request: Request,
                              response: Response,
                              db: AsyncSession = Depends(get_db)):
    """
    Refresh the access token using a valid refresh token.

    This endpoint extracts the refresh token from the HTTP-only cookie, verifies it,
    and issues a new access token and refresh token. The old refresh token is revoked
    to prevent replay attacks.

    Args:
        request (Request): The HTTP request object containing the refresh token cookie.
        response (Response): The FastAPI response object for setting cookies.
        db (AsyncSession): The database session.

    Returns:
        TokenResponse: A response containing the new access token.

    Raises:
        HTTPException: If the refresh token is missing, invalid, or expired.
    """
    try:
        new_access_token, new_refresh_token = await rotate_refresh_token(request, db)
        response.set_cookie(key="refresh_token", value=new_refresh_token,
                            httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)

        return {"access_token": new_access_token, "token_type": "Bearer"}

    except HTTPException as e:
        raise e
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500,
                            detail="Token refresh failed due to database error")


@router.get("/{username}/check", response_model=BasicTaskResponse)
async def client_auth_username_check(username: str,
                                     request: Request,
                                     db: AsyncSession = Depends(get_db)):
    """
    Check if the provided username matches the client associated with the refresh token.

    This endpoint verifies that the refresh token is valid and belongs to the client
    with the specified username. This can be used for additional security checks.
    The refresh token is extracted from the request cookies.

    Args:
        username (str): The username to verify against the token.
        request (Request): The HTTP request object containing the refresh token cookie.
        db (AsyncSession): The database session dependency.

    Returns:
        BasicTaskResponse: A response indicating the success of the check.

    Raises:
        HTTPException: If the refresh token is missing, invalid, or the username doesn't match.
    """
    try:
        refresh_token_obj = await verify_refresh_token(request, db)
        client = await db.execute(select(Client).where(Client.uuid == refresh_token_obj.client_uuid))
        client = client.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=401,
                                detail="Invalid token")

        if client.username != username:
            raise HTTPException(status_code=403,
                                detail="Username mismatch")

        return {"result": "success"}

    except HTTPException as e:
        raise e
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500,
                            detail="Check failed due to server error")
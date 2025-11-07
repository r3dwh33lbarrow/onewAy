from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.logger import get_logger
from app.models.user import User
from app.schemas.general import BasicTaskResponse, TokenResponse
from app.schemas.user_auth import *
from app.services.authentication import TokenType, create_access_token, get_current_user
from app.services.password import hash_password

router = APIRouter(prefix="/user/auth")
logger = get_logger()


@router.post("/login", response_model=BasicTaskResponse)
async def user_auth_login(
    user_login_request: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and create login session.

    Validates user credentials and creates an authenticated session by setting
    an HTTP-only access token cookie. Updates the user's last login timestamp.
    The cookie expires after 7 days.

    Args:
        user_login_request: UserLoginRequest containing username and password
        response: HTTP response object to set cookies
        db: Database session dependency

    Returns:
        BasicTaskResponse: Success/failure result

    Raises:
        HTTPException: 401 if username or password is invalid
        HTTPException: 500 if login process fails
    """
    logger.debug(
        "User login attempt for '%s'",
        user_login_request.username,
    )

    user = await db.execute(
        select(User).where(User.username == user_login_request.username)
    )
    user = user.scalar_one_or_none()

    if not user or not user.verify_password(user_login_request.password):
        logger.warning("Invalid credentials for user '%s'", user_login_request.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    try:
        access_token = create_access_token(user.uuid, TokenType.USER)
        user.last_login = datetime.now(UTC)
        await db.commit()

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
        )
        logger.info("User '%s' logged in", user.username)
        return {"result": "success"}
    except HTTPException as e:
        raise e
    except Exception:
        await db.rollback()
        logger.exception("Login failure for user '%s'", user_login_request.username)
        raise HTTPException(status_code=500, detail="Failed to sign in user")


@router.post("/logout", response_model=BasicTaskResponse)
async def user_auth_logout(response: Response):
    """
    Log out the current user by clearing authentication cookie.

    Removes the access token cookie from the client, effectively logging out
    the user from the system.

    Args:
        response: HTTP response object to delete cookies

    Returns:
        BasicTaskResponse: Success result
    """
    response.delete_cookie(key="access_token", httponly=True, samesite="lax")
    logger.info("User logged out")
    return {"result": "success"}


@router.post("/ws-token", response_model=TokenResponse)
async def user_auth_ws_token(user: User = Depends(get_current_user)):
    """
    Generate a WebSocket authentication token for the current user.

    Creates a special access token that can be used for WebSocket connections.
    This token is separate from the regular HTTP authentication token and is
    specifically designed for WebSocket authentication.

    Args:
        user: Current authenticated user dependency

    Returns:
        TokenResponse: WebSocket access token and token type

    Raises:
        HTTPException: 401 if user is not authenticated
    """
    logger.debug("Issued websocket token for user '%s'", user.username)
    ws_token = create_access_token(user.uuid, TokenType.WEBSOCKET)
    return {"access_token": ws_token, "token_type": "websocket"}

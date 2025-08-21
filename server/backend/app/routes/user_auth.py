from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.dependencies import get_db
from app.models.user import User
from app.schemas.general import BasicTaskResponse
from app.schemas.user_auth import UserSignupRequest, UserSigninRequest
from app.services.authentication import hash_password, create_access_token

router = APIRouter(prefix="/user/auth")


@router.post("/register", response_model=BasicTaskResponse)
async def user_auth_register(signup_request: UserSignupRequest, db: AsyncSession = Depends(get_db)):
    """
    Handles user registration by creating a new user in the database.

    Args:
        signup_request (UserSignupRequest): The request body containing the username and password for the new user.
        db (AsyncSession): The database session dependency, provided by FastAPI's `Depends`.

    Raises:
        HTTPException:
            - 409 Conflict: If a user with the given username already exists.
            - 500 Internal Server Error: If there is an error while adding the user to the database.
    """
    existing_user = await db.execute(select(User).where(User.username == signup_request.username))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    new_user = User(
        username=signup_request.username,
        hashed_password=hash_password(signup_request.password)
    )

    try:
        db.add(new_user)
        await db.commit()
        return {"result": "success"}

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to add user to the database")


@router.post("/login", response_model=BasicTaskResponse)
async def user_auth_login(signin_request: UserSigninRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """
    Handles user login by verifying credentials and generating an access token.

    Args:
        signin_request (UserSigninRequest): The request body containing the username and password for authentication.
        response (Response): The HTTP response object used to set cookies.
        db (AsyncSession): The database session dependency, provided by FastAPI's `Depends`.

    Raises:
        HTTPException:
            - 401 Unauthorized: If the username or password is invalid.
            - 500 Internal Server Error: If there is an error during the login process.

    Returns:
        dict: A response indicating the success of the operation, with the key "result" set to "success".
    """
    user = await db.execute(select(User).where(User.username == signin_request.username))
    user = user.scalar_one_or_none()

    if not user or not user.verify_password(signin_request.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    try:
        access_token = create_access_token(user.uuid, True)
        user.last_login = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()

        response.set_cookie(key="access_token", value=access_token,
                            httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)
        return {"result": "success"}
    except HTTPException as e:
        raise e
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to sign in user")

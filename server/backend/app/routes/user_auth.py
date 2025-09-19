from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.user import User
from app.schemas.general import BasicTaskResponse, TokenResponse
from app.schemas.user_auth import UserLoginRequest, UserRegisterRequest
from app.services.authentication import TokenType, create_access_token, get_current_user
from app.services.password import hash_password

router = APIRouter(prefix="/user/auth")


@router.post("/register", response_model=BasicTaskResponse)
async def user_auth_register(
    user_register_request: UserRegisterRequest, db: AsyncSession = Depends(get_db)
):
    existing_user = await db.execute(
        select(User).where(User.username == user_register_request.username)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    new_user = User(
        username=user_register_request.username,
        hashed_password=hash_password(user_register_request.password),
    )

    try:
        db.add(new_user)
        await db.commit()
        return {"result": "success"}

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to add user to the database"
        )


@router.post("/login", response_model=BasicTaskResponse)
async def user_auth_login(
    user_login_request: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await db.execute(
        select(User).where(User.username == user_login_request.username)
    )
    user = user.scalar_one_or_none()

    if not user or not user.verify_password(user_login_request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    try:
        access_token = create_access_token(user.uuid, True)
        user.last_login = datetime.now(UTC)
        await db.commit()

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
        )
        return {"result": "success"}
    except HTTPException as e:
        raise e
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to sign in user")


@router.post("/logout", response_model=BasicTaskResponse)
async def user_auth_logout(response: Response):
    response.delete_cookie(key="access_token", httponly=True, samesite="lax")
    return {"result": "success"}


@router.post("/ws-token", response_model=TokenResponse)
async def user_auth_ws_token(user: User = Depends(get_current_user)):
    ws_token = create_access_token(user.uuid, TokenType.WEBSOCKET)
    return {"access_token": ws_token, "token_type": "websocket"}

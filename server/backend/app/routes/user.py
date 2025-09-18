import os
import uuid

import magic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from app.dependencies import get_db
from app.models.user import User
from app.schemas.general import BasicTaskResponse
from app.schemas.user import UserInfoResponse, UserUpdateRequest
from app.services.authentication import get_current_user
from app.settings import settings

router = APIRouter(prefix="/user")


@router.get("/get-avatar")
async def user_get_avatar(user: User = Depends(get_current_user)):
    """
    Retrieve the avatar image for the currently authenticated user.

    Args:
        user (User): The currently authenticated user, injected via dependency.

    Returns:
        FileResponse: The avatar image file for the user if it exists, or the default
        avatar image if the user's avatar is not set or the file is missing.

    Raises:
        HTTPException:
            - 500: If the default avatar image is missing from the configuration.
    """
    if user.avatar_path:
        filepath = os.path.join(settings.avatar_directory, user.avatar_path)
        if os.path.exists(filepath):
            return FileResponse(filepath, media_type="image/png")

    default_path = os.path.join(settings.avatar_directory, "default_avatar.png")
    if not os.path.exists(default_path):
        raise HTTPException(
            status_code=500, detail="Configuration error: default_avatar.png missing"
        )
    return FileResponse(default_path, media_type="image/png")


@router.post("/update-avatar", response_model=BasicTaskResponse)
async def user_update_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update the avatar image for the currently authenticated user.

    Args:
        file (UploadFile): The uploaded avatar file, expected to be a PNG image.
        db (AsyncSession): The database session, injected via dependency.
        user (User): The currently authenticated user, injected via dependency.

    Returns:
        BasicTaskResponse: A response indicating the success of the operation.

    Raises:
        HTTPException:
            - 400: If the file is not a PNG, is empty, or exceeds the maximum size.
            - 413: If the file size exceeds the allowed limit.
            - 500: If there is an error saving the file or committing to the database.
    """
    if file.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Avatar must be a PNG file")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(contents) > settings.max_avatar_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {settings.max_avatar_size // (1024*1024)}MB",
        )

    if magic.from_buffer(contents, mime=True) != "image/png":
        raise HTTPException(status_code=400, detail="Avatar must be a PNG file")

    avatar_path = f"{uuid.uuid4()}_{user.username}.png"
    try:
        with open(os.path.join(settings.avatar_directory, avatar_path), "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save avatar: {e}")

    user.avatar_path = avatar_path
    try:
        await db.commit()
        return {"result": "success"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/me", response_model=UserInfoResponse)
async def user_get_me(user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's public profile information.

    Returns username, admin flag, timestamps, and avatar presence.
    """
    return UserInfoResponse(
        username=user.username,
        is_admin=bool(user.is_admin),
        last_login=user.last_login,
        created_at=user.created_at,
        avatar_set=bool(user.avatar_path),
    )


@router.put("/me", response_model=BasicTaskResponse)
async def user_update_me(
    payload: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update current user's editable fields.

    Currently supports updating username (must be unique).
    """
    try:
        if payload.username is not None:
            new_username = payload.username.strip()
            if len(new_username) == 0:
                raise HTTPException(status_code=400, detail="Username cannot be empty")

            if new_username != user.username:
                existing = await db.execute(
                    select(User).where(User.username == new_username)
                )
                if existing.scalar_one_or_none():
                    raise HTTPException(
                        status_code=409, detail="Username already exists"
                    )
                user.username = new_username

        await db.commit()
        return {"result": "success"}

    except HTTPException as e:
        await db.rollback()
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user: {e}")

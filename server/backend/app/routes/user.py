import os
from pathlib import Path

import aiofiles
import magic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from app.dependencies import get_db
from app.logger import get_logger
from app.models.user import User
from app.schemas.general import BasicTaskResponse
from app.schemas.user import *
from app.services.authentication import get_current_user
from app.settings import settings

router = APIRouter(prefix="/user")
logger = get_logger()


@router.get("/me", response_model=UserInfoResponse)
async def user_get_me(user: User = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.

    Args:
        user: Currently authenticated user

    Returns:
        User information including username, admin status, login times, and avatar status
    """
    logger.debug("Returning profile for user '%s'", user.username)
    return UserInfoResponse(
        username=user.username,
        is_admin=user.is_admin,
        last_login=user.last_login,
        created_at=user.created_at,
        avatar_set=True if user.avatar_path else False,
    )


@router.patch("", response_model=BasicTaskResponse)
async def user_patch(
    update_info: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update user information (currently supports username changes).

    Args:
        update_info: User data to update (only provided fields will be updated)
        db: Database session for executing queries
        user: Currently authenticated user to update

    Returns:
        Success status of the update operation

    Raises:
        HTTPException: 400 if username is empty, 409 if username already exists,
                      500 if database error occurs
    """
    logger.debug(
        "User '%s' update payload received", user.username
    )

    try:
        if update_info.username is not None:
            new_username = update_info.username.strip()
            if len(new_username) == 0:
                logger.warning("User '%s' attempted to set empty username", user.username)
                raise HTTPException(status_code=400, detail="Username cannot be empty")

            if new_username != user.username:
                existing = await db.execute(
                    select(User).where(User.username == new_username)
                )
                if existing.scalar_one_or_none():
                    logger.warning(
                        "User '%s' attempted to change to existing username '%s'",
                        user.username,
                        new_username,
                    )
                    raise HTTPException(
                        status_code=409, detail="Username already exists"
                    )
                user.username = new_username
                await db.commit()

        logger.info("User '%s' updated profile", user.username)
        return {"result": "success"}

    except HTTPException as e:
        await db.rollback()
        logger.warning(
            "User '%s' update aborted: %s", user.username, e.detail
        )
        raise e
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to update user '%s'", user.username)
        raise HTTPException(status_code=500, detail=f"Failed to update user: {e}")


@router.get("/avatar")
async def user_get_avatar(user: User = Depends(get_current_user)):
    """
    Retrieve the user's avatar image or return default avatar.

    Args:
        user: Currently authenticated user

    Returns:
        PNG image file (user's custom avatar or default avatar)

    Raises:
        HTTPException: 500 if default avatar file is missing

    Note:
        Returns user's custom avatar if set, otherwise returns default avatar
    """
    if user.avatar_path:
        file_path = Path(settings.paths.avatar_dir) / user.avatar_path
        if os.path.exists(file_path):
            logger.debug("Serving avatar for user '%s'", user.username)
            return FileResponse(file_path, media_type="image/png")

    default_path = Path(settings.paths.avatar_dir) / "default_avatar.png"
    if not os.path.exists(default_path):
        logger.error("Default avatar missing at %s", default_path)
        raise HTTPException(
            status_code=500, detail="Default avatar file does not exist"
        )
    logger.debug("Serving default avatar for user '%s'", user.username)
    return FileResponse(default_path, media_type="image/png")


@router.put("/avatar", response_model=BasicTaskResponse)
async def user_put_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Upload and set a new avatar image for the user.

    Args:
        file: PNG image file to upload as avatar
        db: Database session for executing queries
        user: Currently authenticated user

    Returns:
        Success status of the avatar upload operation

    Raises:
        HTTPException: 400 if file is not PNG or empty, 413 if file too large,
                      500 if file save or database error occurs

    Note:
        File must be PNG format and under the configured size limit.
        Validates file type using both content-type header and magic bytes.
    """
    if file.content_type != "image/png":
        logger.warning(
            "User '%s' uploaded avatar with invalid content type '%s'",
            user.username,
            file.content_type,
        )
        raise HTTPException(status_code=400, detail="Avatar must be a PNG file")

    contents = await file.read()
    if len(contents) == 0:
        logger.warning("User '%s' uploaded empty avatar file", user.username)
        raise HTTPException(status_code=400, detail="Empty file")

    if len(contents) > settings.other.max_avatar_size_mb * 1024 * 1024:
        logger.warning(
            "User '%s' avatar upload too large (%d bytes)",
            user.username,
            len(contents),
        )
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {settings.other.max_avatar_size_mb}MB",
        )

    if magic.from_buffer(contents, mime=True) != "image/png":
        logger.warning("User '%s' avatar failed PNG validation", user.username)
        raise HTTPException(status_code=400, detail="Avatar must be a PNG file")

    avatar_path = f"{user.uuid}.png"
    try:
        async with aiofiles.open(
            Path(settings.paths.avatar_dir) / avatar_path, "wb"
        ) as f:
            await f.write(contents)
    except Exception as e:
        logger.exception("Failed to write avatar for user '%s'", user.username)
        raise HTTPException(status_code=500, detail=f"Failed to save avatar: {e}")

    user.avatar_path = avatar_path
    try:
        await db.commit()
        logger.info("User '%s' updated avatar", user.username)
        return {"result": "success"}
    except Exception as e:
        await db.rollback()
        logger.exception("Database error updating avatar for user '%s'", user.username)
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

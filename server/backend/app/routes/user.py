import os
from pathlib import Path

import aiofiles
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


@router.get("/me", response_model=UserInfoResponse)
async def user_get_me(user: User = Depends(get_current_user)):
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
    try:
        if update_info.username is not None:
            new_username = update_info.username.strip()
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


@router.get("/avatar")
async def user_get_avatar(user: User = Depends(get_current_user)):
    if user.avatar_path:
        file_path = Path(settings.paths.avatar_dir) / user.avatar_path
        if os.path.exists(file_path):
            return FileResponse(file_path, media_type="image/png")

    default_path = Path(settings.paths.avatar_dir) / "default_avatar.png"
    if not os.path.exists(default_path):
        raise HTTPException(
            status_code=500, detail="Default avatar file does not exist"
        )
    return FileResponse(default_path, media_type="image/png")


@router.put("/avatar", response_model=BasicTaskResponse)
async def user_put_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):

    if file.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Avatar must be a PNG file")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(contents) > settings.other.max_avatar_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {settings.other.max_avatar_size_mb}MB",
        )

    if magic.from_buffer(contents, mime=True) != "image/png":
        raise HTTPException(status_code=400, detail="Avatar must be a PNG file")


    avatar_path = f"{user.uuid}.png"
    try:
        async with aiofiles.open(Path(settings.paths.avatar_dir) / avatar_path, "wb") as f:
            await f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save avatar: {e}")

    user.avatar_path = avatar_path
    try:
        await db.commit()
        return {"result": "success"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

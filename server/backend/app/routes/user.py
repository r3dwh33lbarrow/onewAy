import magic

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import Response

from app.dependencies import get_db
from app.models.user import User
from app.services.authentication import get_current_user
from app.settings import settings

router = APIRouter(prefix="/user")


@router.get("/get-avatar")
async def user_get_avatar(user: User = Depends(get_current_user)):
    """
    Retrieve the avatar for the currently authenticated user.

    This endpoint checks if the authenticated user has a custom avatar.
    If a custom avatar exists, it returns the binary content of the avatar
    with the appropriate media type (`image/png`). If no custom avatar is
    found, it attempts to return the default avatar from the file system.

    Args:
        user (User): The currently authenticated user, injected via dependency.

    Returns:
        Response: A FastAPI Response object containing the avatar image
        (either the user's custom avatar or the default avatar) with the
        `image/png` media type.

    Raises:
        HTTPException: If the default avatar file is not found or if an
        unexpected error occurs while retrieving the avatar.
    """
    if user.avatar:
        return Response(content=user.avatar, media_type="image/png")

    try:
        with open(settings.default_avatar, "rb") as file:
            return Response(content=file.read(), media_type="image/png")
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration error. DEFAULT_AVATAR does not exist"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user avatar"
        )


@router.post("/update-avatar")
async def user_update_avatar(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Update the avatar for the currently authenticated user.

    This endpoint allows the user to upload a new avatar image. The uploaded file
    is validated to ensure it meets the size and format requirements. If the file
    is valid, it is saved as the user's new avatar.

    Args:
        file (UploadFile): The uploaded file containing the new avatar image.
        db (AsyncSession): The database session, injected via dependency.
        user (User): The currently authenticated user, injected via dependency.

    Returns:
        dict: A dictionary containing the result of the operation.

    Raises:
        HTTPException: If the file size cannot be read, if the file exceeds the
        maximum allowed size, if the file is not a PNG image, or if there is an
        error saving the avatar to the database.
    """
    if not file.size:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file size"
        )

    if file.size > settings.max_avatar_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large Maximum size is {settings.max_avatar_size // (1024*1024)}MB"
        )

    contents = await file.read()
    if not magic.from_buffer(contents, mime=True) == "image/png":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be a PNG file"
        )

    user.avatar = contents
    db.add(user)
    try:
        await db.commit()
        return {"result": "success"}
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save avatar"
        )
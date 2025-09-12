from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from starlette.responses import Response

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
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.module import Module
from app.schemas.user_modules import UserModuleAllResponse, ModuleInfo
from app.services.authentication import verify_access_token

router = APIRouter(prefix="/user/modules")


@router.get("/all", response_model=UserModuleAllResponse)
async def user_modules_all(db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)):
    result = await db.execute(select(Module))
    modules = result.scalars().all()

    module_list = [
        ModuleInfo(
            name=module.name,
            path=module.path,
            version=module.version
        ) for module in modules
    ]
    return UserModuleAllResponse(modules=module_list)

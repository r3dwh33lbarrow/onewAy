from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.module import Module
from app.models.module_bucket import ModuleBucket
from app.schemas.general import BasicTaskResponse
from app.schemas.module_bucket import BucketData, AllBucketsResponse
from app.services.authentication import get_current_user, verify_access_token, get_current_client

router = APIRouter(prefix="/module")


async def get_module(module_name: str, db: AsyncSession) -> Module:
    module = await db.execute(
        select(Module).options(selectinload(Module.bucket)).where(Module.name == module_name)
    )
    module = module.scalar_one_or_none()
    if not module:
        raise HTTPException(
            status_code=404,
            detail="Module not found"
        )

    if not module.bucket:
        raise HTTPException(
            status_code=400,
            detail="No bucket exists for module"
        )

    return module


@router.post("/new-bucket", response_model=BasicTaskResponse)
async def module_new_bucket(module_name: str, db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)):
    module = await db.execute(
        select(Module).options(selectinload(Module.bucket)).where(Module.name == module_name)
    )
    module = module.scalar_one_or_none()
    if not module:
        raise HTTPException(
            status_code=404,
            detail="Module not found"
        )

    if module.bucket:
        raise HTTPException(
            status_code=400,
            detail="Bucket for module already exists"
        )

    module.bucket = ModuleBucket()
    try:
        await db.commit()
        await db.refresh(module)
        return {"result": "success"}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to add bucket to module in database"
        )


@router.get("/bucket", response_model=BucketData)
async def module_get_bucket(module_name: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    module = await get_module(module_name, db)
    module.bucket.consume()

    try:
        await db.commit()
        await db.refresh(module)
        return {"data": module.bucket.data}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to consume bucket"
        )


@router.put("/bucket", response_model=BasicTaskResponse)
async def module_put_bucket(module_name: str, bucket_info: BucketData, db: AsyncSession = Depends(get_db), _=Depends(get_current_client)):
    module = await get_module(module_name, db)
    module.bucket.data = module.bucket.data + bucket_info.data
    if module.bucket.remove_at:
        module.bucket.remove_at = None

    try:
        await db.commit()
        await db.refresh(module)
        return {"result": "success"}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to append to bucket in database"
        )



@router.delete("/bucket", response_model=BasicTaskResponse)
async def module_delete_bucket(module_name: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    module = await get_module(module_name, db)

    module.bucket = None
    try:
        await db.commit()
        await db.refresh(module)
        return {"result": "success"}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete bucket in database"
        )


@router.get("/all-buckets", response_model=AllBucketsResponse)
async def module_all_buckets(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    all_buckets = await db.execute(select(ModuleBucket))
    all_buckets = all_buckets.scalars().all()
    bucket_names = {}

    for bucket in all_buckets:
        bucket_names[bucket.module_name] = "consumed" if bucket.remove_at else "not consumed"
    return {"buckets": bucket_names}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models.module import Module
from app.models.module_bucket import ModuleBucket
from app.schemas.general import BasicTaskResponse
from app.schemas.module_bucket import AllBucketsResponse, BucketData, BucketInfo
from app.services.authentication import (
    get_current_client,
    get_current_user,
    verify_access_token,
)

router = APIRouter(prefix="/module")


async def get_module(module_name: str, db: AsyncSession) -> Module:
    """
    Retrieve a module by name and ensure it has an associated bucket.

    Args:
        module_name: The unique name of the module to look up.
        db: Async SQLAlchemy session dependency.

    Returns:
        Module: The module instance with its bucket relationship loaded.

    Raises:
        HTTPException: 404 if the module is not found.
        HTTPException: 400 if the module exists but has no bucket.
    """
    module = await db.execute(
        select(Module)
        .options(selectinload(Module.bucket))
        .where(Module.name == module_name)
    )
    module = module.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    if not module.bucket:
        raise HTTPException(status_code=400, detail="No bucket exists for module")

    return module


@router.post("/new-bucket", response_model=BasicTaskResponse)
async def module_new_bucket(
    module_name: str, db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)
):
    """
    Create a new, empty bucket for a given module.

    If the module already has a bucket, the request fails with 400. This endpoint
    requires a valid access token.

    Args:
        module_name: The name of the module to attach a new bucket to.
        db: Async SQLAlchemy session dependency.
        _: Access token verification dependency.

    Returns:
        BasicTaskResponse: Result indicating success.

    Raises:
        HTTPException: 404 if the module is not found.
        HTTPException: 400 if a bucket already exists for the module.
        HTTPException: 500 if the database operation fails.
    """
    module = await db.execute(
        select(Module)
        .options(selectinload(Module.bucket))
        .where(Module.name == module_name)
    )
    module = module.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    if module.bucket:
        raise HTTPException(status_code=400, detail="Bucket for module already exists")

    module.bucket = ModuleBucket()
    try:
        await db.commit()
        await db.refresh(module)
        return {"result": "success"}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to add bucket to module in database"
        )


@router.get("/bucket", response_model=BucketData)
async def module_get_bucket(
    module_name: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)
):
    """
    Retrieve and mark a module's bucket as consumed.

    Returns the current bucket data and sets a removal timestamp (consume) so the
    bucket is marked as consumed for future reference.

    Args:
        module_name: The name of the module whose bucket data is requested.
        db: Async SQLAlchemy session dependency.
        _: Current user authentication dependency.

    Returns:
        BucketData: The bucket data payload.

    Raises:
        HTTPException: 404 if the module is not found.
        HTTPException: 400 if the module has no bucket.
        HTTPException: 500 if the consume/database operation fails.
    """
    module = await get_module(module_name, db)
    module.bucket.consume()

    try:
        await db.commit()
        await db.refresh(module)
        return {"data": module.bucket.data}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to consume bucket")


@router.put("/bucket", response_model=BasicTaskResponse)
async def module_put_bucket(
    module_name: str,
    bucket_info: BucketData,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_client),
):
    """
    Append data to a module's bucket, clearing its removal marker if present.

    This endpoint is intended for client usage. If the bucket was previously
    marked for removal (consumed), the removal time is cleared.

    Args:
        module_name: The name of the module whose bucket will be updated.
        bucket_info: Payload containing data to append to the bucket.
        db: Async SQLAlchemy session dependency.
        _: Current client authentication dependency.

    Returns:
        BasicTaskResponse: Result indicating success.

    Raises:
        HTTPException: 404 if the module is not found.
        HTTPException: 400 if the module has no bucket.
        HTTPException: 500 if the database operation fails.
    """
    module = await get_module(module_name, db)
    module.bucket.data = module.bucket.data + bucket_info.data + "\n"
    if module.bucket.remove_at:
        module.bucket.remove_at = None

    try:
        await db.commit()
        await db.refresh(module)
        return {"result": "success"}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to append to bucket in database"
        )


@router.delete("/bucket", response_model=BasicTaskResponse)
async def module_delete_bucket(
    module_name: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)
):
    """
    Delete a module's bucket.

    Removes the association by setting the module's bucket to None. Depending on
    ORM configuration, this will also delete the bucket row via cascade.

    Args:
        module_name: The name of the module whose bucket should be deleted.
        db: Async SQLAlchemy session dependency.
        _: Current user authentication dependency.

    Returns:
        BasicTaskResponse: Result indicating success.

    Raises:
        HTTPException: 404 if the module is not found.
        HTTPException: 400 if the module has no bucket.
        HTTPException: 500 if the database operation fails.
    """
    module = await get_module(module_name, db)

    module.bucket = None
    try:
        await db.commit()
        await db.refresh(module)
        return {"result": "success"}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to delete bucket in database"
        )


@router.get("/all-buckets", response_model=AllBucketsResponse)
async def module_all_buckets(
    db: AsyncSession = Depends(get_db), _=Depends(get_current_user)
):
    """
    List all module buckets and their consumption status.

    Iterates over all buckets and returns a mapping of module name to a simple
    status string: "consumed" if the bucket has a removal timestamp set, otherwise
    "not consumed".

    Args:
        db: Async SQLAlchemy session dependency.
        _: Current user authentication dependency.

    Returns:
        AllBucketsResponse: Mapping of module_name -> consumption status.
    """
    all_buckets = await db.execute(select(ModuleBucket))
    all_buckets = all_buckets.scalars().all()
    buckets = []

    for bucket in all_buckets:
        buckets.append(
            BucketInfo(
                name=bucket.module_name,
                consumed=True if bucket.remove_at else False,
                created_at=bucket.created_at,
            )
        )
    return {"buckets": buckets}

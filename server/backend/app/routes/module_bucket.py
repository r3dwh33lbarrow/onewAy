from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models.module import Module
from app.models.module_bucket import ModuleBucket, ModuleBucketEntry
from app.schemas.general import BasicTaskResponse
from app.schemas.module_bucket import (
    AllBucketsResponse,
    BucketData,
    BucketInfo,
    ModuleBucketResponse,
)
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
        .options(
            selectinload(Module.bucket)
            .selectinload(ModuleBucket.entries)
            .selectinload(ModuleBucketEntry.client)
        )
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


@router.get("/bucket", response_model=ModuleBucketResponse)
async def module_get_bucket(
    module_name: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)
):
    """
    Retrieve all client-specific entries for a module's bucket and mark them as consumed.

    Args:
        module_name: The name of the module whose bucket data is requested.
        db: Async SQLAlchemy session dependency.
        _: Current user authentication dependency.

    Returns:
        ModuleBucketResponse: The bucket data grouped by client.

    Raises:
        HTTPException: 404 if the module is not found.
        HTTPException: 400 if the module has no bucket.
        HTTPException: 500 if the consume/database operation fails.
    """
    module = await get_module(module_name, db)
    bucket = module.bucket
    response_entries = []
    sorted_entries = sorted(
        bucket.entries,
        key=lambda entry: (
            entry.client.username if entry.client else "",
            entry.created_at,
        ),
    )

    for entry in sorted_entries:
        if entry.data and entry.remove_at is None:
            entry.consume()

        response_entries.append(
            {
                "uuid": entry.uuid,
                "client_username": entry.client.username if entry.client else None,
                "data": entry.data,
                "consumed": entry.remove_at is not None,
                "created_at": entry.created_at,
                "remove_at": entry.remove_at,
            }
        )

    try:
        await db.commit()
        return {"module_name": module.bucket.module_name, "entries": response_entries}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to consume bucket")


@router.put("/bucket", response_model=BasicTaskResponse)
async def module_put_bucket(
    module_name: str,
    bucket_info: BucketData,
    db: AsyncSession = Depends(get_db),
    current_client=Depends(get_current_client),
):
    """
    Append data to a module's bucket, clearing its removal marker if present.

    This endpoint is intended for client usage. If the bucket was previously
    marked for removal (consumed), the removal time is cleared.

    Args:
        module_name: The name of the module whose bucket will be updated.
        bucket_info: Payload containing data to append to the bucket.
        db: Async SQLAlchemy session dependency.
        current_client: Current client authentication dependency.

    Returns:
        BasicTaskResponse: Result indicating success.

    Raises:
        HTTPException: 404 if the module is not found.
        HTTPException: 400 if the module has no bucket.
        HTTPException: 500 if the database operation fails.
    """
    module = await get_module(module_name, db)
    bucket = module.bucket
    entry = next(
        (item for item in bucket.entries if item.client_uuid == current_client.uuid),
        None,
    )

    if not entry:
        entry = ModuleBucketEntry(bucket=bucket, client=current_client, data="")
        bucket.entries.append(entry)

    entry.data = entry.data + bucket_info.data + "\n"
    entry.client = current_client
    if entry.remove_at:
        entry.remove_at = None

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


@router.delete("/bucket-entry", response_model=BasicTaskResponse)
async def module_delete_bucket_entry(
    module_name: str,
    entry_uuid: UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Delete a single entry within a module bucket."""

    module = await get_module(module_name, db)
    bucket = module.bucket

    entry = next((item for item in bucket.entries if item.uuid == entry_uuid), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Bucket entry not found")

    try:
        await db.delete(entry)
        await db.commit()
        return {"result": "success"}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to delete bucket entry in database"
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
    all_entries = await db.execute(
        select(ModuleBucketEntry).options(
            selectinload(ModuleBucketEntry.bucket),
            selectinload(ModuleBucketEntry.client),
        )
    )
    all_entries = all_entries.scalars().all()
    buckets = []

    for entry in all_entries:
        bucket = entry.bucket
        if not bucket:
            continue
        if not entry.data or not entry.data.strip():
            continue
        buckets.append(
            BucketInfo(
                name=bucket.module_name,
                consumed=True if entry.remove_at else False,
                created_at=entry.created_at,
                client_username=entry.client.username if entry.client else None,
                entry_uuid=entry.uuid,
            )
        )
    return {"buckets": buckets}

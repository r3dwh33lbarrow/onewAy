import os

from fastapi import APIRouter, Depends, File
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.logger import get_logger
from app.models.client_module import ClientModule
from app.schemas.general import BasicTaskResponse
from app.schemas.module import *
from app.services.authentication import get_current_user, verify_access_token
from app.services.client_websockets import client_websocket_manager
from app.services.module import *
from app.settings import settings
from app.utils import convert_to_snake_case, hyphen_to_snake_case

router = APIRouter(prefix="/module")
logger = get_logger()


@router.get("/all", response_model=UserModuleAllResponse)
async def module_all(
    db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)
):
    """
    Retrieve all available modules from the database.

    Returns a list of all modules with their basic information including name,
    description, version, start configuration, and supported binary platforms.

    Args:
        db: Database session dependency
        _: Access token verification dependency

    Returns:
        UserModuleAllResponse: Response containing a list of all modules with basic info

    Raises:
        HTTPException: 401 if access token is invalid
    """
    result = await db.execute(select(Module))
    modules = result.scalars().all()

    module_list = [
        ModuleBasicInfo(
            name=module.name,
            description=module.description,
            version=module.version,
            start=module.start,
            binaries_platform=list(module.binaries.keys()) if module.binaries else [],
        )
        for module in modules
    ]
    logger.debug("Retrieved %d modules", len(module_list))
    return UserModuleAllResponse(modules=module_list)


@router.put("/add", response_model=BasicTaskResponse)
async def module_add(
    request: ModuleAddRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Add a new module to the system from a local path.

    Validates the module path exists, loads the module configuration from config.yaml,
    and adds the module to the database. Supports both absolute and relative paths.

    Args:
        request: ModuleAddRequest containing the module path
        db: Database session dependency
        _: Current user authentication dependency

    Returns:
        BasicTaskResponse: Success/failure result

    Raises:
        HTTPException: 400 if module path doesn't exist
        HTTPException: 500 if database operation fails
    """
    logger.debug("Module add request for path %s", request.module_path)
    relative_module_path = Path(settings.paths.module_dir) / request.module_path

    if not os.path.exists(request.module_path):
        if not os.path.exists(relative_module_path):
            logger.warning(
                "Module add failed: path '%s' not found", request.module_path
            )
            raise HTTPException(status_code=400, detail="Module path does not exist")
        else:
            module_path = relative_module_path
    else:
        module_path = request.module_path

    config_path = Path(module_path) / "config.yaml"
    config = await load_config_yaml(config_path)

    try:
        new_module = create_module_from_config(config)
        db.add(new_module)
        await db.commit()
        await db.refresh(new_module)
        logger.info("Module '%s' added", new_module.name)
        return {"result": "success"}
    except Exception:
        await db.rollback()
        logger.exception("Failed to add module from path %s", module_path)
        raise HTTPException(
            status_code=500, detail="Failed to add module to the database"
        )


@router.put("/upload")
async def module_upload(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Upload and install a new module from uploaded files.

    Processes uploaded files, validates the module configuration, creates the module
    directory structure, and adds the module to the database. Includes cleanup on failure.

    Args:
        files: List of uploaded files containing the module
        db: Database session dependency
        _: Current user authentication dependency

    Returns:
        dict: Success result with list of saved files

    Raises:
        HTTPException: 409 if module already exists
        HTTPException: 500 if upload processing or database operation fails
    """
    module_dir = None
    logger.debug("Module upload received %d files", len(files))
    try:
        saved, module_dir = await process_uploaded_files(files)

        config_path = module_dir / "config.yaml"
        config = load_config_yaml_sync(config_path)

        validate_config_structure(config)
        new_module = create_module_from_config(config)

        if await check_module_exists(db, new_module.name):
            logger.warning(
                "Module upload aborted: module '%s' already exists", new_module.name
            )
            raise HTTPException(status_code=409, detail="Module already exists")

        db.add(new_module)
        await db.commit()

        logger.info("Module '%s' uploaded", new_module.name)
        logger.debug("Module upload saved files: %s", saved)
        return {"result": "success", "files_saved": saved}

    except HTTPException as exc:
        logger.warning("Module upload failed: %s", getattr(exc, "detail", exc))
        raise
    except Exception:
        await db.rollback()
        logger.exception("Unexpected error during module upload")
        raise HTTPException(
            status_code=500, detail="Failed to add module to the database"
        )


@router.get("/get/{module_name}")
async def module_get(
    module_name: str, db: AsyncSession = Depends(get_db), _=Depends(verify_access_token)
):
    """
    Retrieve detailed information for a specific module.

    Fetches module details including name, description, version, and binary configurations
    for the specified module.

    Args:
        module_name: Name of the module to retrieve (supports hyphen format)
        db: Database session dependency
        _: Access token verification dependency

    Returns:
        dict: Module details including name, description, version, and binaries

    Raises:
        HTTPException: 404 if module not found
        HTTPException: 401 if access token is invalid
    """
    module_name = hyphen_to_snake_case(module_name)
    logger.debug("Fetching module '%s'", module_name)
    module = await get_module_by_name(db, module_name)

    if not module:
        logger.warning("Module '%s' not found", module_name)
        raise HTTPException(status_code=404, detail="Module not found")

    logger.debug("Returning details for module '%s'", module.name)
    return {
        "name": module.name,
        "description": module.description,
        "version": module.version,
        "binaries": module.binaries,
    }


@router.put("/update/{module_name}", response_model=BasicTaskResponse)
async def module_update(
    module_name: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Update an existing module with new files and configuration.

    Updates an existing module by replacing its files and configuration. Creates backups
    before modification and handles rollback on failure. Supports module renaming.

    Args:
        module_name: Name of the module to update (supports hyphen format)
        files: List of uploaded files containing the updated module
        db: Database session dependency
        _: Current user authentication dependency

    Returns:
        BasicTaskResponse: Success/failure result

    Raises:
        HTTPException: 404 if module not found
        HTTPException: 500 if update operation fails
    """
    module_name = hyphen_to_snake_case(module_name)
    logger.debug("Module update initiated for '%s'", module_name)
    existing_module = await get_module_by_name(db, module_name)

    if not existing_module:
        logger.warning("Module '%s' not found for update", module_name)
        raise HTTPException(status_code=404, detail="Module not found")

    module_path = Path(settings.paths.module_dir) / module_name
    backup_path = create_backup_and_cleanup(module_path)
    logger.debug("Created backup for module '%s' at %s", module_name, backup_path)

    try:
        saved, module_dir = await process_uploaded_files(files)

        config_path = module_dir / "config.yaml"
        config = load_config_yaml_sync(config_path)

        validate_config_structure(config)
        binaries = process_binaries_field(config.get("binaries"))

        new_module_name = convert_to_snake_case(config["name"])
        existing_module.name = new_module_name
        existing_module.description = config.get("description")
        existing_module.version = config["version"]
        existing_module.start = config["start"]
        existing_module.binaries = binaries

        await db.commit()

        if new_module_name != module_name:
            new_module_path = Path(settings.paths.module_dir) / new_module_name
            if new_module_path.exists():
                shutil.rmtree(new_module_path, ignore_errors=True)
            shutil.move(module_dir, new_module_path)
            logger.info(
                "Module '%s' renamed to '%s' during update",
                module_name,
                new_module_name,
            )

        if backup_path and backup_path.exists():
            shutil.rmtree(backup_path)

        logger.info("Module '%s' updated", new_module_name)
        return {"result": "success"}

    except HTTPException as exc:
        restore_from_backup(backup_path, module_path)
        logger.warning(
            "Module update failed for '%s': %s",
            module_name,
            getattr(exc, "detail", exc),
        )
        raise
    except Exception as e:
        await db.rollback()
        restore_from_backup(backup_path, module_path)
        logger.exception("Unexpected error updating module '%s'", module_name)
        raise HTTPException(status_code=500, detail=f"Failed to update module: {e}")


@router.delete("/delete/{module_name}", response_model=BasicTaskResponse)
async def module_delete(
    module_name: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)
):
    """
    Delete a module from the system.

    Removes the module from the database and deletes its associated files and directory
    from the filesystem.

    Args:
        module_name: Name of the module to delete (supports hyphen format)
        db: Database session dependency
        _: Current user authentication dependency

    Returns:
        BasicTaskResponse: Success/failure result

    Raises:
        HTTPException: 404 if module not found
        HTTPException: 500 if deletion operation fails
    """
    module_name = hyphen_to_snake_case(module_name)
    logger.debug("Module delete requested for '%s'", module_name)
    module = await get_module_by_name(db, module_name)

    if not module:
        logger.warning("Module '%s' not found for deletion", module_name)
        raise HTTPException(status_code=404, detail="Module not found")

    try:
        await db.delete(module)
        await db.commit()

        module_path = Path(settings.paths.module_dir) / module_name
        if os.path.exists(module_path):
            shutil.rmtree(module_path)

        logger.info("Module '%s' deleted", module_name)
        return {"result": "success"}

    except Exception:
        await db.rollback()
        logger.exception("Failed to delete module '%s'", module_name)
        raise HTTPException(status_code=500, detail="Failed to delete module")


@router.get("/query-module-dir", response_model=ModuleDirectoryContents)
async def module_query_module_dir(_=Depends(get_current_user)):
    """
    Query the contents of the module directory.

    Lists all files and directories in the module directory, categorizing them
    as either files or directories.

    Args:
        _: Current user authentication dependency

    Returns:
        ModuleDirectoryContents: Directory contents with files and directories listed

    Raises:
        HTTPException: 500 if directory access fails
    """
    contents_list = []
    try:
        for item in os.listdir(settings.paths.module_dir):
            item_path = os.path.join(settings.paths.module_dir, item)
            if os.path.isfile(item_path):
                contents_list.append({"file": item})
            elif os.path.isdir(item_path):
                contents_list.append({"directory": item})
    except Exception as e:
        logger.exception("Failed to list module directory contents")
        raise HTTPException(
            status_code=500, detail=f"Failed to query module directory: {str(e)}"
        )

    logger.debug("Module directory listing returned %d items", len(contents_list))
    return {"contents": contents_list}


@router.get("/installed/{client_username}")
async def module_installed_client_username(
    client_username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_access_token),
):
    """
    Get all modules installed on a specific client.

    Retrieves the list of modules installed on the specified client, including
    module details and installation status.

    Args:
        client_username: Username of the client to query
        db: Database session dependency
        _: Access token verification dependency

    Returns:
        list[InstalledModuleInfo]: List of installed modules with their details and status

    Raises:
        HTTPException: 400 if client username not found
        HTTPException: 401 if access token is invalid
    """
    client = await db.execute(
        select(Client)
        .options(selectinload(Client.client_modules).selectinload(ClientModule.module))
        .where(Client.username == client_username)
    )
    client = client.scalar_one_or_none()

    if not client:
        logger.warning(
            "Module install lookup failed: client '%s' not found", client_username
        )
        raise HTTPException(status_code=400, detail="Client username not found")

    mod_names = []
    for client_mod in client.client_modules:
        mod_info = InstalledModuleInfo(
            name=client_mod.module.name,
            description=client_mod.module.description,
            version=client_mod.module.version,
            status=client_mod.status,
        )
        mod_names.append(mod_info)

    logger.debug(
        "Client '%s' has %d installed modules", client_username, len(mod_names)
    )
    return mod_names


@router.post("/set-installed/{client_username}")
async def module_set_installed_client_username(
    client_username: str,
    module_name: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_access_token),
):
    """
    Mark a module as installed on a specific client.

    Associates a module with a client, marking it as installed. Prevents duplicate
    installations on the same client.

    Args:
        client_username: Username of the client
        module_name: Name of the module to mark as installed
        db: Database session dependency
        _: Access token verification dependency

    Returns:
        dict: Success result

    Raises:
        HTTPException: 400 if client username or module not found
        HTTPException: 409 if module already installed on client
        HTTPException: 500 if database operation fails
    """
    client = await get_client_by_username(db, client_username)
    if not client:
        logger.warning("Set installed failed: client '%s' not found", client_username)
        raise HTTPException(status_code=400, detail="Client username not found")

    module = await get_module_by_name(db, module_name)
    if not module:
        logger.warning("Set installed failed: module '%s' not found", module_name)
        raise HTTPException(status_code=400, detail="Module not found")

    client_with_modules = await db.execute(
        select(Client)
        .options(selectinload(Client.client_modules).selectinload(ClientModule.module))
        .where(Client.username == client_username)
    )
    client_with_modules = client_with_modules.scalar_one_or_none()

    for client_mod in client_with_modules.client_modules:
        if client_mod.module.name == module.name:
            logger.warning(
                "Module '%s' already installed on client '%s'",
                module.name,
                client.username,
            )
            raise HTTPException(
                status_code=409, detail="Module already installed on client"
            )

    client_module = ClientModule(
        client_name=client.username, module_name=module.name, status="installed"
    )

    client.client_modules.append(client_module)
    db.add(client_module)
    try:
        await db.commit()
        logger.info(
            "Module '%s' marked installed for client '%s'",
            module.name,
            client.username,
        )
    except IntegrityError:
        await db.rollback()
        logger.exception(
            "Database integrity error installing module '%s' for client '%s'",
            module.name,
            client.username,
        )
        raise HTTPException(
            status_code=500, detail="Failed to add installed module to the database"
        )

    return {"result": "success"}


@router.get("/run/{module_name}")
async def module_run_module_name(
    module_name: str,
    client_username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Send a command to run a module on a specific client.

    Sends a websocket message to the specified client to run the given module.
    Only works for modules configured for manual start.

    Args:
        module_name: Name of the module to run
        client_username: Username of the target client
        db: Database session dependency
        _: Current user authentication dependency

    Returns:
        dict: Success result

    Raises:
        HTTPException: 400 if module not installed on client or not configured for manual start
        HTTPException: 404 if module or client not found
    """
    logger.debug(
        "Module run requested: module='%s', client='%s'",
        module_name,
        client_username,
    )
    logger.debug(
        "Module cancel requested: module='%s', client='%s'",
        module_name,
        client_username,
    )
    module, client = await validate_module_and_client(db, module_name, client_username)

    client_module = await db.execute(
        select(ClientModule).where(
            (ClientModule.client_name == client_username)
            & (ClientModule.module_name == module.name)
        )
    )
    client_module = client_module.scalar_one_or_none()
    if not client_module:
        logger.warning(
            "Module '%s' not installed on client '%s'",
            module.name,
            client_username,
        )
        raise HTTPException(status_code=400, detail="Module not installed on client")

    if (module.start or "").lower() != "manual":
        logger.warning("Module '%s' is not configured for manual start", module.name)
        raise HTTPException(
            status_code=400, detail="Module is not configured for manual start"
        )

    await client_websocket_manager.send_to_client(
        client_uuid=str(client.uuid),
        message={"message_type": "module_run", "module_name": module.name},
    )

    logger.info(
        "Run command sent for module '%s' to client '%s'",
        module.name,
        client_username,
    )
    return {"result": "success"}


@router.get("/cancel/{module_name}")
async def module_cancel_module_name(
    module_name: str,
    client_username: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Send a command to cancel a running module on a specific client.

    Sends a websocket message to the specified client to cancel/stop the given module.

    Args:
        module_name: Name of the module to cancel
        client_username: Username of the target client
        db: Database session dependency
        _: Current user authentication dependency

    Returns:
        dict: Success result

    Raises:
        HTTPException: 400 if module or client validation fails
        HTTPException: 404 if module or client not found
    """
    module, client = await validate_module_and_client(db, module_name, client_username)

    await client_websocket_manager.send_to_client(
        client_uuid=str(client.uuid),
        message={"message_type": "module_cancel", "module_name": module.name},
    )

    logger.info(
        "Cancel command sent for module '%s' to client '%s'",
        module.name,
        client_username,
    )
    return {"result": "success"}

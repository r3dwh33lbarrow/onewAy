import asyncio
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import update

from app.logger import get_logger, logger_fix
from app.routes import client_auth
from app.settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    An asynchronous context manager for the FastAPI application lifecycle.
    This function runs Alembic migrations on startup.
    """
    log, formatter = get_logger()
    log.info("Starting up and running migrations...")
    alembic_cfg = Config("alembic.ini")
    
    db_url = settings.database_url
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_cfg.set_main_option("configure_logger", "false")

    try:
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
        logger_fix(log, formatter)
        log.info("Migrations applied successfully.")

        from app.dependencies import get_db
        from app.models.client import Client

        async for db in get_db():
            await db.execute(update(Client).values(alive=False))
            await db.commit()
            log.info("All clients marked as not alive")
    except Exception as e:
        log.error(f"Error applying migrations: {e}")

    yield
    
    log.info("Shutting down...")

app = FastAPI(lifespan=lifespan)
app.include_router(client_auth.router)

@app.get("/")
async def root():
    return {"message": "onewAy API"}

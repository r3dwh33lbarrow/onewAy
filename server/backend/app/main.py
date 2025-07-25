import asyncio
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.logger import get_logger
from app.routes import client_auth
from app.settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    An asynchronous context manager for the FastAPI application lifecycle.
    This function runs Alembic migrations on startup.
    """
    log = get_logger()
    log.info("Starting up and running migrations...")
    alembic_cfg = Config("alembic.ini")
    
    db_url = settings.database_url
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    try:
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
        log.info("Migrations applied successfully.")
    except Exception as e:
        log.error(f"Error applying migrations: {e}")

    yield
    
    log.info("Shutting down...")

app = FastAPI(lifespan=lifespan)
app.include_router(client_auth.router)

@app.get("/")
async def root():
    return {"message": "onewAy API"}

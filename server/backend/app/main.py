import asyncio
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import update
from starlette.middleware.cors import CORSMiddleware

from app.dependencies import get_db, cleanup_db, init_db
from app.logger import get_logger
from app.models.client import Client
from app.routes import client_auth, user_auth, client
from app.settings import settings, load_test_settings

if settings.testing:
    settings = load_test_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    An asynchronous context manager for the FastAPI application lifecycle.
    This function runs Alembic migrations on startup.
    """
    log = get_logger()
    if not settings.testing:
        log.info("Starting up and running migrations...")
        alembic_cfg = Config("alembic.ini")

        db_url = settings.database_url
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_cfg.set_main_option("configure_logger", "false")

        try:
            await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
            log.info("Migrations completed successfully")

            async for db in get_db():
                await db.execute(update(Client).values(alive=False))
                await db.commit()
                log.info("All clients marked as not alive")

        except Exception as e:
            log.error(f"Error applying migrations: {e}")
            raise

    else:
        await init_db()

    yield

    if not settings.testing:
        await cleanup_db()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(client_auth.router)
app.include_router(user_auth.router)
app.include_router(client.router)

@app.get("/")
async def root():
    return {"message": "onewAy API"}

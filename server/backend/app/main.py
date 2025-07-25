from dotenv import load_dotenv
load_dotenv()
# ---
import asyncio
import os
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from app.routes import client_auth


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    An asynchronous context manager for the FastAPI application lifecycle.
    This function runs Alembic migrations on startup.
    """
    print("Starting up and running migrations...")
    alembic_cfg = Config("alembic.ini")
    
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    try:
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
        print("Migrations applied successfully.")
    except Exception as e:
        print(f"Error applying migrations: {e}")

    yield
    
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)
app.include_router(client_auth.router)


@app.get("/")
async def root():
    return {"message": "onewAy API"}

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import update
from starlette.middleware.cors import CORSMiddleware

from app.dependencies import cleanup_db, get_db, init_db
from app.logger import get_logger
from app.models.client import Client
from app.routes import (
    client,
    client_auth,
    module,
    module_bucket,
    user,
    user_auth,
    user_generate_client,
    websockets,
)
from app.settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    log = get_logger()
    if settings.testing and settings.testing.testing:
        log.info(f"{'=' * 10} TESTING MODE {'=' * 10}")
        await init_db()

    else:
        try:
            async for db in get_db():
                await db.execute(update(Client).values(alive=False))
                await db.commit()
                log.info("All clients marked not alive")
        except Exception as e:
            log.exception("Failed to mark all clients as not alive: %s", e)
            raise e

    yield

    if settings.testing and settings.testing.testing:
        await cleanup_db()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(client_auth.router)
app.include_router(user_auth.router)
app.include_router(client.router)
app.include_router(websockets.router)
app.include_router(module.router)
app.include_router(user.router)
app.include_router(module_bucket.router)
app.include_router(user_generate_client.router)


@app.get("/")
async def root():
    return {"message": "onewAy API"}

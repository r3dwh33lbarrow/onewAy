from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.routes import client, client_auth, user, user_auth, user_modules, websockets
from app.settings import settings

app = FastAPI()
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
app.include_router(user_modules.router)
app.include_router(user.router)


@app.get("/")
async def root():
    return {"message": "onewAy API"}

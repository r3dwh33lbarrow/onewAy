from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


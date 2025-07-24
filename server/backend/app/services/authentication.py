from fastapi.security import HTTPBearer
from passlib.context import CryptContext

security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["scrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

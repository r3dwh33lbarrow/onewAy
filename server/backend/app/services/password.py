from passlib.context import CryptContext

# Password context for hashing and verifying passwords
pwd_context = CryptContext(schemes=["scrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using scrypt hashing algorithm.

    Args:
        password: The plaintext password to be hashed

    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: The plaintext password to verify
        hashed_password: The hashed password to verify against

    Returns:
        bool: True if the password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

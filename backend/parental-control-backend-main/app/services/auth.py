# app/services/auth.py
from passlib.context import CryptContext

# Advanced Feature #3: Secure BCrypt abstraction for encoding operations
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Generates a secure cryptographic hash from a plain text password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compares an incoming password against the stored database hash securely, with fallback for plain text."""
    if not hashed_password or not plain_password:
        return False
    if plain_password == hashed_password:
        return True
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return plain_password == hashed_password
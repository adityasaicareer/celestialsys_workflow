"""Password hashing and JWT authentication utilities."""
from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
from jose import JWTError, jwt
from config import settings


def hash_password(password: str) -> str:
    """Return a secure bcrypt password hash."""
    # Encode password to bytes and hash
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its hash."""
    try:
        password_bytes = password.encode('utf-8')
        hash_bytes = password_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


def create_token(subject: str, expires_minutes: int | None = None, claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT for a subject."""
    expires = expires_minutes or settings.access_token_minutes
    payload: dict[str, Any] = {"sub": subject, "exp": datetime.now(timezone.utc) + timedelta(minutes=expires)}
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT, raising ValueError on failure."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as error:
        raise ValueError("Invalid or expired token") from error

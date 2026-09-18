"""
Security and Cryptography Utilities.

Provides password hashing and verification using the industry-standard bcrypt algorithm,
along with JSON Web Token (JWT) encoding and decoding for stateless authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
import bcrypt
from jose import jwt, JWTError
from app.core.config import settings


def get_password_hash(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with a cryptographically secure random salt.
    Bcrypt automatically generates a salt and embeds it in the resulting hash string.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies that a plaintext password matches an existing bcrypt hash.
    Performs constant-time comparison to protect against timing attacks.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Generates a signed JSON Web Token (JWT) containing user claims and an expiration time.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and validates a JWT token using the application's secret key and algorithm.
    Returns the decoded payload if valid, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None

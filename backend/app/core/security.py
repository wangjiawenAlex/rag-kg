"""
Security utilities.

Handles JWT, password hashing, and authentication.
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
    
    Returns:
        True if passwords match
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    secret_key: str,
    expires_delta: Optional[timedelta] = None,
    algorithm: str = "HS256"
) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Claims to encode
        secret_key: Secret key for signing
        expires_delta: Token expiration time
        algorithm: JWT algorithm
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256"
) -> Optional[dict]:
    """
    Decode and verify JWT token.
    
    Args:
        token: JWT token
        secret_key: Secret key for verification
        algorithm: JWT algorithm
    
    Returns:
        Decoded claims or None if invalid
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

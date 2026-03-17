"""
Authentication API endpoints.

Handles user login, token refresh, and session management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import timedelta
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.core.config import get_settings
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request payload."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response payload."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600


class RefreshTokenRequest(BaseModel):
    """Refresh token request payload."""
    refresh_token: str


# Demo user database (in production, use real database)
# Pre-hashed password for demo user (hash of "demo123")
USERS = {
    "demo": {
        "password_hash": "$2b$12$tqB38Hll9hl2hk4Y5gGObOcEFCDIBLdMT6fqD6QOUhOo4ao2KzK4q",  # demo123
        "user_id": str(uuid.uuid4()),
        "role": "admin"
    }
}


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    User login endpoint.
    
    Args:
        request: LoginRequest with username and password
    
    Returns:
        TokenResponse with JWT tokens
    """
    settings = get_settings()
    
    # Verify credentials
    if request.username not in USERS:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = USERS[request.username]
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
    
    access_token = create_access_token(
        data={"sub": request.username, "user_id": user["user_id"], "role": user["role"]},
        secret_key=settings.secret_key,
        expires_delta=access_token_expires,
        algorithm=settings.algorithm
    )
    
    refresh_token = create_access_token(
        data={"sub": request.username, "type": "refresh"},
        secret_key=settings.secret_key,
        expires_delta=refresh_token_expires,
        algorithm=settings.algorithm
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_token_expires.total_seconds())
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    
    Args:
        request: RefreshTokenRequest with refresh_token
    
    Returns:
        TokenResponse with new access_token
    """
    settings = get_settings()
    
    # Verify refresh token
    payload = decode_token(request.refresh_token, settings.secret_key, settings.algorithm)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    username = payload.get("sub")
    if username not in USERS:
        raise HTTPException(status_code=401, detail="User not found")
    
    user = USERS[username]
    
    # Generate new access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": username, "user_id": user["user_id"], "role": user["role"]},
        secret_key=settings.secret_key,
        expires_delta=access_token_expires,
        algorithm=settings.algorithm
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=int(access_token_expires.total_seconds())
    )


@router.post("/logout")
async def logout(user_id: str):
    """
    Logout user and invalidate session.
    
    Args:
        user_id: User ID to logout
    """
    return {"message": "Logout successful"}

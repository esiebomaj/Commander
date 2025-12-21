"""
Authentication module for Commander backend.

Provides JWT verification and user extraction from Supabase tokens.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from .config import settings
from .user_context import set_current_user_id


# HTTP Bearer token scheme for extracting JWT from Authorization header
security = HTTPBearer()


@dataclass
class User:
    """Authenticated user information extracted from JWT."""
    id: str  # Supabase user UUID
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


def verify_token(token: str) -> dict:
    """
    Verify a Supabase JWT token and return the payload.
    
    Args:
        token: The JWT token to verify
    
    Returns:
        The decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.
    
    Extracts and verifies the JWT from the Authorization header,
    then returns a User object with the user's information.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    
    Args:
        credentials: The HTTP Authorization credentials (automatically injected)
    
    Returns:
        User object with id, email, and metadata
    
    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extract user info from token payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user metadata from token
    user_metadata = payload.get("user_metadata", {})
    
    # Set user ID in context for access anywhere in the request
    set_current_user_id(user_id)
    
    return User(
        id=user_id,
        email=payload.get("email"),
        full_name=user_metadata.get("full_name"),
        avatar_url=user_metadata.get("avatar_url"),
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[User]:
    """
    FastAPI dependency to optionally get the current user.
    
    Unlike get_current_user, this does not raise an error if no
    authentication is provided. Useful for endpoints that work
    differently for authenticated vs anonymous users.
    
    Args:
        credentials: The HTTP Authorization credentials (optional)
    
    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

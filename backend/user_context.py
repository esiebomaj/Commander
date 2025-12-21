"""
User context management using contextvars.

This module provides a way to access the current user ID from anywhere
in the application without passing it through every function call.

Usage:
    # In auth middleware/dependency - set the user
    set_current_user_id(user.id)
    
    # Anywhere else - get the user
    user_id = get_current_user_id()
"""
from contextvars import ContextVar
from typing import Optional

# Context variable to store the current user ID
_current_user_id: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)


def set_current_user_id(user_id: str) -> None:
    """Set the current user ID in the context."""
    _current_user_id.set(user_id)


def get_current_user_id() -> str:
    """
    Get the current user ID from the context.
    
    Raises:
        RuntimeError: If no user ID is set (not in an authenticated request)
    """
    user_id = _current_user_id.get()
    if user_id is None:
        raise RuntimeError("No user ID set in context. Are you inside an authenticated request?")
    return user_id


def get_current_user_id_optional() -> Optional[str]:
    """Get the current user ID, or None if not set."""
    return _current_user_id.get()


def clear_current_user_id() -> None:
    """Clear the current user ID from context."""
    _current_user_id.set(None)

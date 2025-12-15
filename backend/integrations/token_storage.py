"""
Token storage for OAuth credentials.

Stores tokens securely in a JSON file in the data directory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from ..config import settings


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

TOKENS_FILE = settings.data_dir / "tokens.json"


# --------------------------------------------------------------------------- #
# Token Storage Functions
# --------------------------------------------------------------------------- #

def _load_tokens() -> Dict[str, Any]:
    """Load all tokens from the JSON file."""
    try:
        if TOKENS_FILE.exists():
            return json.loads(TOKENS_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return {}


def _save_tokens(tokens: Dict[str, Any]) -> None:
    """Save tokens to the JSON file."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2, default=str))


def save_token(service: str, token_data: Dict[str, Any]) -> None:
    """
    Save OAuth token data for a service.
    
    Args:
        service: The service name (e.g., "gmail", "slack")
        token_data: Token data including access_token, refresh_token, etc.
    """
    tokens = _load_tokens()
    tokens[service] = {
        **token_data,
        "updated_at": datetime.utcnow().isoformat(),
    }
    _save_tokens(tokens)


def get_token(service: str) -> Optional[Dict[str, Any]]:
    """
    Get OAuth token data for a service.
    
    Args:
        service: The service name (e.g., "gmail", "slack")
    
    Returns:
        Token data dict or None if not found
    """
    tokens = _load_tokens()
    return tokens.get(service)


def delete_token(service: str) -> bool:
    """
    Delete OAuth token for a service.
    
    Args:
        service: The service name (e.g., "gmail", "slack")
    
    Returns:
        True if token was deleted, False if it didn't exist
    """
    tokens = _load_tokens()
    if service in tokens:
        del tokens[service]
        _save_tokens(tokens)
        return True
    return False


def has_token(service: str) -> bool:
    """Check if a service has stored credentials."""
    return get_token(service) is not None


def list_services() -> list[str]:
    """List all services with stored tokens."""
    return list(_load_tokens().keys())


# --------------------------------------------------------------------------- #
# Gmail-specific helpers
# --------------------------------------------------------------------------- #

def save_gmail_history_id(history_id: str) -> None:
    """
    Save the last Gmail history ID for incremental sync.
    
    Args:
        history_id: The Gmail history ID to save
    """
    tokens = _load_tokens()
    if "gmail" not in tokens:
        tokens["gmail"] = {}
    tokens["gmail"]["last_history_id"] = history_id
    tokens["gmail"]["history_updated_at"] = datetime.utcnow().isoformat()
    _save_tokens(tokens)


def get_gmail_history_id() -> Optional[str]:
    """Get the last Gmail history ID for incremental sync."""
    tokens = _load_tokens()
    gmail_data = tokens.get("gmail", {})
    return gmail_data.get("last_history_id")

"""
Google OAuth integration utilities.

Provides a base class for building Google API integrations with
common OAuth flow, credential management, and service initialization.
"""
from .oauth import GoogleOAuthClient

__all__ = ["GoogleOAuthClient"]

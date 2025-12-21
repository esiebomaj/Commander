"""
Gmail integration for Commander.

Provides OAuth authentication, email reading, sending, and push notifications.
"""
from .client import GmailIntegration, get_gmail
from .orchestrator import (
    process_new_emails,
    sync_recent_emails,
    setup_push_notifications,
)
from .routes import router
from .tools import (
    GMAIL_TOOLS,
    GMAIL_TOOL_EXECUTORS,
    gmail_send_email,
    gmail_create_draft,
)

__all__ = [
    # Gmail client
    "GmailIntegration",
    "get_gmail",
    
    # Orchestrator functions
    "process_new_emails",
    "sync_recent_emails",
    "setup_push_notifications",

    # API Router
    "router",

    # Tools (for LLM + execution)
    "GMAIL_TOOLS",
    "GMAIL_TOOL_EXECUTORS",
    "gmail_send_email",
    "gmail_create_draft",
]

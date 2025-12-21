"""
Integrations package for Commander.

This package contains integrations with external services like Gmail, Slack, etc.
Each integration has its own subfolder.
"""
from .gmail import (
    GmailIntegration,
    get_gmail,
    process_new_emails,
    sync_recent_emails,
)

__all__ = [
    # Gmail
    "GmailIntegration",
    "get_gmail",
    "process_new_emails",
    "sync_recent_emails",
]

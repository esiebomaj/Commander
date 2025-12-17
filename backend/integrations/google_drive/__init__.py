"""
Google Drive integration for Commander.

Provides OAuth authentication and meeting transcript fetching.
"""
from .client import (
    DriveIntegration,
    get_drive,
    get_connected_drive,
    get_drive_status,
    disconnect_drive,
)
from .routes import router
from .transcript_processor import (
    process_new_transcript,
    analyze_transcript,
    format_metadata_summary,
)

__all__ = [
    "DriveIntegration",
    "get_drive",
    "get_connected_drive",
    "get_drive_status",
    "disconnect_drive",
    # API Router
    "router",
    # Processing
    "process_new_transcript",
    "analyze_transcript",
    "format_metadata_summary",
]


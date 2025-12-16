"""
Google Calendar integration for Commander.

Provides OAuth authentication and calendar event creation.
"""
from .client import (
    CalendarIntegration,
    get_calendar,
    get_calendar_status,
    disconnect_calendar,
)
from .routes import router
from .tools import (
    CALENDAR_TOOLS,
    CALENDAR_TOOL_EXECUTORS,
    schedule_meeting,
)

__all__ = [
    "CalendarIntegration",
    "get_calendar",
    "get_calendar_status",
    "disconnect_calendar",
    # API Router
    "router",
    # Tools
    "CALENDAR_TOOLS",
    "CALENDAR_TOOL_EXECUTORS",
    "schedule_meeting",
]

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
    "CALENDAR_TOOLS",
    "CALENDAR_TOOL_EXECUTORS",
    "schedule_meeting",
]

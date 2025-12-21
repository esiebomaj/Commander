"""
Central tool registry for Commander.

Each tool defines both the LLM schema and execution logic.
Tools are registered by action type for easy dispatch.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .models import ActionType
from .user_context import get_current_user_id


# --------------------------------------------------------------------------- #
# Tool Input Schemas
# --------------------------------------------------------------------------- #

class CreateTodoInput(BaseModel):
    """Input for creating a todo item."""
    title: str = Field(..., description="Title of the todo item")
    notes: Optional[str] = Field(None, description="Additional notes")
    due_date: Optional[str] = Field(None, description="Due date (ISO format)")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


# --------------------------------------------------------------------------- #
# Core Tools (schema + execution)
# --------------------------------------------------------------------------- #

@tool(args_schema=CreateTodoInput)
def create_todo(
    title: str,
    notes: Optional[str] = None,
    due_date: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create a follow-up task in the user's todo list."""
    user_id = get_current_user_id()
    # TODO: Integrate with todo API per user
    return {
        "success": True,
        "note": "Todo created (mock)",
        "user_id": user_id,
        "title": title,
        "notes": notes,
        "due_date": due_date,
    }


# --------------------------------------------------------------------------- #
# Tool Registry
# --------------------------------------------------------------------------- #

# Core tools list (for LLM binding)
CORE_TOOLS = [create_todo]

# Import integration tools
from .integrations.gmail.tools import GMAIL_TOOLS, GMAIL_TOOL_EXECUTORS
from .integrations.google_calendar.tools import CALENDAR_TOOLS, CALENDAR_TOOL_EXECUTORS

# All tools for LLM
ALL_TOOLS = GMAIL_TOOLS + CALENDAR_TOOLS + CORE_TOOLS

# Map ActionType to executor function
TOOL_EXECUTORS: Dict[ActionType, Callable] = {
    ActionType.CREATE_TODO: create_todo,
} | GMAIL_TOOL_EXECUTORS | CALENDAR_TOOL_EXECUTORS


def execute_tool(action_type: ActionType, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool by action type with the given payload.
    
    Note: The user context must be set before calling this function.
    Use set_current_user_id() or ensure you're in an authenticated request.
    
    Args:
        action_type: The ActionType enum value
        payload: Tool parameters
    
    Returns:
        Execution result dict
    """
    executor = TOOL_EXECUTORS.get(action_type)
    if not executor:
        return {"success": False, "error": f"No executor for action type: {action_type}"}
    
    try:
        # Tools now get user_id from context via get_current_user_id()
        return executor.invoke(payload)
    except Exception as e:
        return {"success": False, "error": str(e)}

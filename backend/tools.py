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
from datetime import datetime, timezone as tz

from .models import ActionType, ExecutionResult, ProposedAction



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

# Import integration tools (sync)
from .integrations.gmail.tools import GMAIL_TOOLS, GMAIL_TOOL_EXECUTORS
from .integrations.google_calendar.tools import CALENDAR_TOOLS, CALENDAR_TOOL_EXECUTORS

# Import async GitHub tools getter
from .integrations.github.tools import get_github_tools

from .integrations.slack.tools import get_slack_tools

async def get_all_tools(user_id: str) -> Dict[ActionType, Callable]:
    """Get all tool executors, including GitHub executors."""
    github_read_tools, github_write_tools = await get_github_tools(user_id)
    slack_read_tools, slack_write_tools = await get_slack_tools(user_id)

    read_tools = github_read_tools | slack_read_tools
    write_tools = github_write_tools | slack_write_tools | GMAIL_TOOL_EXECUTORS | CALENDAR_TOOL_EXECUTORS | {
        ActionType.CREATE_TODO: create_todo,
    } 

    return read_tools, write_tools



async def execute_tool(action: ProposedAction) -> Dict:

    print(f"[{action.type.value.upper()}] {action.payload}")

    read_tools, write_tools = await get_all_tools(action.user_id)
    executors = read_tools | write_tools
    executor = executors.get(action.type)

    if not executor:
        return {"success": False, "error": f"No executor for action type: {action.type}"}

    result = await executor.ainvoke(action.payload)

    if isinstance(result, dict):
        if "success" in result:
            # our tools return a dict with a success key
            return result
        else:
            # mcp tool error
            error = result.get("error", "Unknown error") + ": " + result.get("details", "")
            return {"success": False, "error": error}
    elif isinstance(result, str):
        # mcp tool success result
        return {"success": True, "output": result}
    else:
        return {"success": False, "error": f"Invalid result type: {type(result)}"}


async def execute_action(action: ProposedAction) -> ExecutionResult:
    """
    Execute an action by dispatching to the appropriate tool.
    
    Note: User context must be set before calling this function.
    The tools will get the user_id from context via get_current_user_id().
    
    Args:
        action: The action to execute
    """
    print(f"[{action.type.value.upper()}] {action.payload}")

    result = await execute_tool(action)
        
    if result.get("success", False):
        return ExecutionResult(
            action_id=action.id,
            status="executed",
            result=result,
            executed_at=datetime.now(tz.utc).isoformat(),
        )
    else:
        return ExecutionResult(
        action_id=action.id,
        status="error",
        result=result,
        executed_at=datetime.now(tz.utc).isoformat(),
    )


"""
Action executor for Commander.

Simply dispatches actions to their corresponding tools.
"""
from __future__ import annotations

from datetime import datetime

from .models import ActionType, ExecutionResult, ProposedAction
from .tools import execute_tool


def execute_action(action: ProposedAction) -> ExecutionResult:
    """
    Execute an action by dispatching to the appropriate tool.
    """
    print(f"[{action.type.value.upper()}] {action.payload}")
    
    result = execute_tool(action.type, action.payload)
    
    # Determine status from result
    if not result.get("success", False):
        status = "error"
    elif result.get("skipped"):
        status = "skipped"
    else:
        status = "executed"
    
    return ExecutionResult(
        action_id=action.id,
        status=status,
        result=result,
        executed_at=datetime.utcnow(),
    )

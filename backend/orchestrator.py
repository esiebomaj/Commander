from __future__ import annotations

from typing import List, Optional

from .context_storage import (
    get_relevant_history,
    get_vector_store,
    save_context,
)
from .tools import execute_action
from .llm import decide_actions_for_context
from .models import ContextItem, ProposedAction
from .storage import (
    get_action,
    list_actions,
    save_action,
    update_action_status,
)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Default number of historical context items to include in LLM prompts
DEFAULT_HISTORY_LIMIT = 10


async def process_new_context(
    user_id: str,
    context: ContextItem,
) -> List[ProposedAction]:
    """
    Process a list of context items through the LLM and persist results.
    
    Args:
        user_id: The user's ID
        context: ContextItem object to process
    
    Returns:
        List of newly created proposed actions
    """
    history_limit = DEFAULT_HISTORY_LIMIT
    created: List[ProposedAction] = []
    store = get_vector_store()

    # Check for duplicate (by source_id from the source system)
    if store.check_exist(user_id, context.source_id, context.source_type):
        print(f"Skipping duplicate context: {context.source_id}")
        return []
    
    # Get relevant history for LLM context (semantic + recent)
    similar_history, recent_history = get_relevant_history(
        user_id=user_id,
        current_context=context,
        semantic_limit=history_limit // 2,
        recent_limit=history_limit // 2,
    )
    
    # Get LLM decisions with history
    actions = await decide_actions_for_context(
        context, 
        similar_history=similar_history,
        recent_history=recent_history
    )
    
    # Create and save proposed actions
    for action_type, payload, confidence in actions:
        proposed = ProposedAction(
            id=0,  # Will be assigned by database
            context_id=context.id,
            type=action_type,
            payload=payload,
            confidence=confidence,
            status="pending",
            source_type=context.source_type,
            sender=context.sender,
            summary=context.summary,
        )
        saved = save_action(user_id, proposed)
        created.append(saved)
        
    # Save the context first 
    context.processed = True
    save_context(user_id, context)
    
    return created


def get_actions(user_id: str, status: Optional[str] = None) -> List[ProposedAction]:
    """
    List actions with optional status filter.
    
    Args:
        user_id: The user's ID
        status: Filter by status (pending, executed, skipped, error)
    """
    return list_actions(user_id=user_id, status=status)


def get_action_by_id(user_id: str, action_id: int) -> Optional[ProposedAction]:
    """Get an action by its ID."""
    return get_action(user_id, action_id)


async def approve_action(user_id: str, action_id: int) -> ProposedAction:
    """
    Approve and execute an action.
    
    Args:
        user_id: The user's ID
        action_id: The ID of the action to approve
    
    Returns:
        The updated action
    
    Raises:
        ValueError: If the action is not found
    """
    action = get_action(user_id, action_id)
    if not action:
        raise ValueError(f"Action {action_id} not found")
    
    if action.status not in ("pending", "error"):
        return action  # no-op if already handled
    
    result = await execute_action(action)

    updated = update_action_status(user_id, action_id, result.status, result.result)
    return updated or action


def skip_action(user_id: str, action_id: int) -> ProposedAction:
    """
    Skip an action (mark it as skipped without executing).
    
    Args:
        user_id: The user's ID
        action_id: The ID of the action to skip
    
    Returns:
        The updated action
    
    Raises:
        ValueError: If the action is not found
    """
    action = get_action(user_id, action_id)
    if not action:
        raise ValueError(f"Action {action_id} not found")
    
    updated = update_action_status(user_id, action_id, "skipped", None)
    return updated or action

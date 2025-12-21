from __future__ import annotations

from typing import List, Optional

from .context_storage import (
    get_relevant_history,
    get_vector_store,
    save_context,
)
from .executors import execute_action
from .llm import decide_actions_for_context
from .models import ContextItem, ProposedAction
from .storage import (
    get_action,
    get_next_action_id,
    list_actions,
    save_action,
    update_action_status,
)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Default number of historical context items to include in LLM prompts
DEFAULT_HISTORY_LIMIT = 10


def process_new_context(
    context: ContextItem,
) -> List[ProposedAction]:
    """
    Process a list of context items through the LLM and persist results.
    
    Args:
        context: ContextItem object to process
    
    Returns:
        List of newly created proposed actions
    """
    history_limit = DEFAULT_HISTORY_LIMIT
    created: List[ProposedAction] = []
    store = get_vector_store()

    # Check for duplicate (by source_id from the source system)
    if store.check_exist(context.source_id, context.source_type):
        print(f"Skipping duplicate context: {context.source_id}")
        return []
    
    # Get relevant history for LLM context (semantic + recent)
    similar_history, recent_history = get_relevant_history(
        current_context=context,
        semantic_limit=history_limit // 2,
        recent_limit=history_limit // 2,
    )
    
    # Get LLM decisions with history
    actions = decide_actions_for_context(
        context, 
        similar_history=similar_history,
        recent_history=recent_history
    )
    
    # Create and save proposed actions
    for action_type, payload, confidence in actions:
        proposed = ProposedAction(
            id=get_next_action_id(),
            context_id=context.id,
            type=action_type,
            payload=payload,
            confidence=confidence,
            status="pending",
            source_type=context.source_type,
            sender=context.sender,
            summary=context.summary,
        )
        save_action(proposed)
        created.append(proposed)
        
    # Save the context first 
    context.processed = True
    save_context(context)
    
    return created


def get_actions(status: Optional[str] = None) -> List[ProposedAction]:
    """
    List actions with optional status filter.
    
    Args:
        status: Filter by status (pending, executed, skipped, error)
    """
    return list_actions(status=status)


def get_action_by_id(action_id: int) -> Optional[ProposedAction]:
    """Get an action by its ID."""
    return get_action(action_id)


def approve_action(action_id: int) -> ProposedAction:
    """
    Approve and execute an action.
    
    Args:
        action_id: The ID of the action to approve
    
    Returns:
        The updated action
    
    Raises:
        ValueError: If the action is not found
    """
    action = get_action(action_id)
    if not action:
        raise ValueError(f"Action {action_id} not found")
    
    if action.status not in ("pending", "error"):
        return action  # no-op if already handled
    
    result = execute_action(action)

    updated = update_action_status(action_id, result.status)
    return updated or action


def skip_action(action_id: int) -> ProposedAction:
    """
    Skip an action (mark it as skipped without executing).
    
    Args:
        action_id: The ID of the action to skip
    
    Returns:
        The updated action
    
    Raises:
        ValueError: If the action is not found
    """
    action = get_action(action_id)
    if not action:
        raise ValueError(f"Action {action_id} not found")
    
    updated = update_action_status(action_id, "skipped")
    return updated or action



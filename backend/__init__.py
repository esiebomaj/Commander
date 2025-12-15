"""
Commander core (MVP) - Python package.

This package contains:
- Generic context storage (JSON-based)
- Adapters for various input sources (email, Slack, etc.)
- Mocked Gmail ingestion
- LLM decision via function-calling with historical context
- Dummy executors
- Orchestrator and FastAPI API
"""

__all__ = [
    "models",
    "storage",
    "adapters",
    "gmail_mock",
    "llm",
    "executors",
    "orchestrator",
    "api",
]

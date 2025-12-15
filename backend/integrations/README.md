# Integrations

This folder contains integrations with external services. Each integration has its own subfolder.

## Available Integrations

| Integration | Status | Description |
|-------------|--------|-------------|
| [Gmail](./gmail/) | ✅ Ready | Read/send emails via Gmail API |

## Structure

Each integration follows a consistent structure:

```
integrations/
├── __init__.py          # Main exports
├── token_storage.py     # Shared OAuth token storage
├── README.md            # This file
└── <service>/
    ├── __init__.py      # Integration exports
    ├── client.py        # API client (OAuth, API calls)
    ├── orchestrator.py  # Integration with Commander (context/actions)
    └── README.md        # Service-specific documentation
```

## Adding a New Integration

1. Create a new folder under `integrations/` (e.g., `integrations/slack/`)
2. Create the required files:
   - `__init__.py` - Export public functions
   - `client.py` - Handle OAuth and API calls
   - `orchestrator.py` - Connect with Commander's context/action system
   - `README.md` - Document setup and usage
3. Use `token_storage.py` for OAuth credential persistence
4. Add API endpoints in `api.py`
5. Update `integrations/__init__.py` to export the new integration

## Token Storage

All integrations share `token_storage.py` for storing OAuth tokens securely in `data/tokens.json`.

```python
from integrations.token_storage import save_token, get_token, delete_token

# Save credentials
save_token("service_name", {"access_token": "...", "refresh_token": "..."})

# Retrieve credentials
token_data = get_token("service_name")

# Remove credentials
delete_token("service_name")
```

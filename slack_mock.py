from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from .models import SlackMessage


def fetch_recent_slack_messages(limit: int = 5) -> List[SlackMessage]:
    """
    Mocked Slack ingestion.
    Returns a small list of recent-looking messages with varied intents.
    """
    now = datetime.now(timezone.utc)
    messages = [
        SlackMessage(
            id="slack_msg_001",
            channel_id="C0123GENERAL",
            channel_name="#general",
            user_id="U001",
            user_name="alice",
            text=(
                "Hey team, reminder that the design review is tomorrow at 2pm. "
                "Please come prepared with your feedback on the new dashboard mockups."
            ),
            timestamp=now - timedelta(hours=1),
            thread_ts=None,
        ),
        SlackMessage(
            id="slack_msg_002",
            channel_id="C0456ENGINEERING",
            channel_name="#engineering",
            user_id="U002",
            user_name="bob",
            text=(
                "@vega Can you take a look at the deployment issue? "
                "The staging env is throwing 500 errors after the latest push."
            ),
            timestamp=now - timedelta(hours=2),
            thread_ts=None,
        ),
        SlackMessage(
            id="slack_msg_003",
            channel_id="C0789RANDOM",
            channel_name="#random",
            user_id="U003",
            user_name="charlie",
            text="Anyone up for lunch at the new ramen place downtown?",
            timestamp=now - timedelta(hours=4),
            thread_ts=None,
        ),
        SlackMessage(
            id="slack_msg_004",
            channel_id="C0456ENGINEERING",
            channel_name="#engineering",
            user_id="U004",
            user_name="diana",
            text=(
                "FYI: I've pushed a hotfix for the auth bug. "
                "Can someone review and approve the PR? It's blocking the release."
            ),
            timestamp=now - timedelta(hours=5),
            thread_ts="1702483200.000100",
        ),
        SlackMessage(
            id="slack_msg_005",
            channel_id="C0111PRODUCT",
            channel_name="#product",
            user_id="U005",
            user_name="eve",
            text=(
                "Quick update: Customer feedback survey results are in. "
                "We should schedule a meeting to discuss the top pain points. "
                "@vega @alice can we find 30 mins this week?"
            ),
            timestamp=now - timedelta(hours=8),
            thread_ts=None,
        ),
    ]
    return messages[:limit]

"""
Platform integrations for CursorBot

Supports:
- Slack: Enterprise workspace integration
"""

from .slack_bot import SlackBot, SlackConfig, SlackUser, SlackMessage, create_slack_bot

__all__ = [
    "SlackBot",
    "SlackConfig",
    "SlackUser",
    "SlackMessage",
    "create_slack_bot",
]

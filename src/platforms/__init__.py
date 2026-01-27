"""
Platform integrations for CursorBot

Supports:
- Slack: Enterprise workspace integration
- Discord Voice: Voice channel listening
"""

from .slack_bot import SlackBot, SlackConfig, SlackUser, SlackMessage, create_slack_bot
from .discord_voice import (
    DiscordVoiceListener, VoiceConfig, VoiceUtterance, VoiceState,
    setup_voice_commands,
)

__all__ = [
    # Slack
    "SlackBot",
    "SlackConfig",
    "SlackUser",
    "SlackMessage",
    "create_slack_bot",
    # Discord Voice
    "DiscordVoiceListener",
    "VoiceConfig",
    "VoiceUtterance",
    "VoiceState",
    "setup_voice_commands",
]

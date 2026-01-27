"""
Platform integrations for CursorBot

Supports:
- Slack: Enterprise workspace integration
- Discord Voice: Voice channel listening
- WhatsApp: WhatsApp Web integration
- MS Teams: Microsoft Teams integration
- iMessage: macOS Messages.app integration
- Line: Line Messaging API integration
"""

from .slack_bot import SlackBot, SlackConfig, SlackUser, SlackMessage, create_slack_bot
from .discord_voice import (
    DiscordVoiceListener, VoiceConfig, VoiceUtterance, VoiceState,
    setup_voice_commands,
)
from .whatsapp_bot import (
    WhatsAppBot, WhatsAppConfig, WhatsAppMessage, WhatsAppChat,
    WhatsAppStatus, format_phone_number, format_group_id, create_whatsapp_bot,
)
from .teams_bot import (
    TeamsBot, TeamsConfig, TeamsUser, TeamsMessage, TeamsStatus,
    create_teams_bot,
)
from .imessage_bot import (
    IMessageBot, IMessageConfig, IMessage, IMessageContact,
    IMessageStatus, create_imessage_bot,
)
from .line_bot import (
    LineBot, LineConfig, LineUser, LineMessage, LineStatus,
    create_line_bot,
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
    # WhatsApp
    "WhatsAppBot",
    "WhatsAppConfig",
    "WhatsAppMessage",
    "WhatsAppChat",
    "WhatsAppStatus",
    "format_phone_number",
    "format_group_id",
    "create_whatsapp_bot",
    # MS Teams
    "TeamsBot",
    "TeamsConfig",
    "TeamsUser",
    "TeamsMessage",
    "TeamsStatus",
    "create_teams_bot",
    # iMessage
    "IMessageBot",
    "IMessageConfig",
    "IMessage",
    "IMessageContact",
    "IMessageStatus",
    "create_imessage_bot",
    # Line
    "LineBot",
    "LineConfig",
    "LineUser",
    "LineMessage",
    "LineStatus",
    "create_line_bot",
]

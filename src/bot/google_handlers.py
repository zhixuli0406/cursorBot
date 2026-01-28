"""
Google Integration Handlers for CursorBot

Provides Telegram commands for:
- /calendar - Google Calendar operations
- /gmail - Gmail operations
- /skills_search - Skills registry search
- /skills_install - Install skills

Usage:
    /calendar - Show today's events
    /calendar week - Show this week's events
    /calendar add <title> <time> - Add event
    
    /gmail - Show recent emails
    /gmail search <query> - Search emails
    /gmail send <to> <subject> <body> - Send email
    
    /skills_search <query> - Search for skills
    /skills_install <skill_id> - Install a skill
"""

from telegram import Update
from telegram.ext import ContextTypes

from ..core.google_calendar import get_calendar_manager, GOOGLE_API_AVAILABLE as CALENDAR_AVAILABLE
from ..core.gmail import get_gmail_manager, GOOGLE_API_AVAILABLE as GMAIL_AVAILABLE
from ..core.skills_registry import get_skills_registry
from ..utils.logger import logger
from ..utils.auth import is_authorized


# ============================================
# Calendar Handlers
# ============================================

async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /calendar command.
    
    Usage:
        /calendar - Show today's events
        /calendar week - Show this week's events
        /calendar add <title> <time> - Add event
        /calendar auth - Start authentication
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not CALENDAR_AVAILABLE:
        await update.message.reply_text(
            "Google API client is not installed.\n\n"
            "Install with:\n"
            "`pip install google-api-python-client google-auth-oauthlib`",
            parse_mode="Markdown"
        )
        return
    
    calendar = get_calendar_manager()
    args = context.args or []
    
    # Handle subcommands
    if not args:
        # Show today's events
        await _show_today_events(update, calendar)
    elif args[0] == "week":
        # Show this week's events
        await _show_week_events(update, calendar)
    elif args[0] == "auth":
        # Start authentication
        await _calendar_auth(update, calendar)
    elif args[0] == "code" and len(args) >= 2:
        # Complete authentication with code
        code = args[1]
        success = await calendar.complete_auth_with_code(code)
        if success:
            await update.message.reply_text("✅ Google Calendar authentication successful!")
        else:
            await update.message.reply_text("❌ Authentication failed. Please try again.")
    elif args[0] == "add" and len(args) >= 3:
        # Add event
        title = args[1]
        time_str = " ".join(args[2:])
        await _add_event(update, calendar, title, time_str)
    elif args[0] == "list":
        # List calendars
        await _list_calendars(update, calendar)
    else:
        await update.message.reply_text(
            "<b>Google Calendar</b>\n\n"
            "Usage:\n"
            "<code>/calendar</code> - Show today's events\n"
            "<code>/calendar week</code> - Show this week's events\n"
            "<code>/calendar list</code> - List calendars\n"
            "<code>/calendar add &lt;title&gt; &lt;time&gt;</code> - Add event\n"
            "<code>/calendar auth</code> - Authenticate\n"
            "<code>/calendar code &lt;code&gt;</code> - Complete auth\n\n"
            "Example:\n"
            "<code>/calendar add Meeting 2026-01-28T14:00</code>",
            parse_mode="HTML"
        )


async def _calendar_auth(update: Update, calendar) -> None:
    """Handle calendar authentication."""
    if calendar.is_authenticated:
        await update.message.reply_text("Already authenticated with Google Calendar.")
        return
    
    auth_url = calendar.get_auth_url()
    if auth_url:
        await update.message.reply_text(
            "<b>Google Calendar Authentication</b>\n\n"
            "1. Click the link below to authenticate\n"
            "2. After approval, you'll be redirected to localhost\n"
            "3. Copy the <code>code</code> parameter from the URL\n"
            "4. Run <code>/calendar code YOUR_CODE</code>\n\n"
            f"<a href=\"{auth_url}\">Click here to authenticate</a>\n\n"
            "<i>Note: The redirect will fail (that's expected). "
            "Just copy the code from the URL.</i>",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        await update.message.reply_text(
            "Cannot generate auth URL.\n\n"
            "Please ensure data/google/credentials.json exists.\n"
            "Download from Google Cloud Console."
        )


async def _show_today_events(update: Update, calendar) -> None:
    """Show today's calendar events."""
    if not calendar.is_authenticated:
        success = await calendar.authenticate()
        if not success:
            await update.message.reply_text(
                "Not authenticated. Run `/calendar auth` first.",
                parse_mode="Markdown"
            )
            return
    
    events = await calendar.get_events_today()
    
    if not events:
        await update.message.reply_text("No events scheduled for today.")
        return
    
    text = "**Today's Events**\n\n"
    for event in events:
        time_str = event.start.strftime("%H:%M") if event.start else "All day"
        text += f"• `{time_str}` - {event.title}\n"
        if event.location:
            text += f"  Location: {event.location}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def _show_week_events(update: Update, calendar) -> None:
    """Show this week's calendar events."""
    if not calendar.is_authenticated:
        success = await calendar.authenticate()
        if not success:
            await update.message.reply_text(
                "Not authenticated. Run `/calendar auth` first.",
                parse_mode="Markdown"
            )
            return
    
    events = await calendar.get_events_week()
    
    if not events:
        await update.message.reply_text("No events scheduled for this week.")
        return
    
    text = "**This Week's Events**\n\n"
    current_date = None
    
    for event in events:
        event_date = event.start.strftime("%Y-%m-%d") if event.start else None
        
        if event_date != current_date:
            current_date = event_date
            day_name = event.start.strftime("%A, %b %d") if event.start else "Unknown"
            text += f"\n**{day_name}**\n"
        
        time_str = event.start.strftime("%H:%M") if event.start else "All day"
        text += f"• `{time_str}` - {event.title}\n"
    
    # Truncate if too long
    if len(text) > 4000:
        text = text[:4000] + "\n\n...(truncated)"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def _list_calendars(update: Update, calendar) -> None:
    """List available calendars."""
    if not calendar.is_authenticated:
        success = await calendar.authenticate()
        if not success:
            await update.message.reply_text(
                "Not authenticated. Run `/calendar auth` first.",
                parse_mode="Markdown"
            )
            return
    
    calendars = await calendar.list_calendars()
    
    if not calendars:
        await update.message.reply_text("No calendars found.")
        return
    
    text = "**Your Calendars**\n\n"
    for cal in calendars:
        primary = " (Primary)" if cal.primary else ""
        text += f"• {cal.name}{primary}\n"
        if cal.description:
            text += f"  _{cal.description}_\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def _add_event(update: Update, calendar, title: str, time_str: str) -> None:
    """Add a calendar event."""
    if not calendar.is_authenticated:
        success = await calendar.authenticate()
        if not success:
            await update.message.reply_text(
                "Not authenticated. Run `/calendar auth` first.",
                parse_mode="Markdown"
            )
            return
    
    try:
        event = await calendar.create_event(
            title=title,
            start=time_str,
        )
        
        if event:
            await update.message.reply_text(
                f"**Event Created**\n\n"
                f"Title: {event.title}\n"
                f"Time: {event.start.strftime('%Y-%m-%d %H:%M')}\n"
                f"[Open in Calendar]({event.link})",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("Failed to create event.")
            
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


# ============================================
# Gmail Handlers
# ============================================

async def gmail_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /gmail command.
    
    Usage:
        /gmail - Show recent emails
        /gmail unread - Show unread emails
        /gmail search <query> - Search emails
        /gmail send <to> <subject> | <body> - Send email
        /gmail auth - Start authentication
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not GMAIL_AVAILABLE:
        await update.message.reply_text(
            "Google API client is not installed.\n\n"
            "Install with:\n"
            "`pip install google-api-python-client google-auth-oauthlib`",
            parse_mode="Markdown"
        )
        return
    
    gmail = get_gmail_manager()
    args = context.args or []
    
    if not args:
        # Show recent emails
        await _show_recent_emails(update, gmail)
    elif args[0] == "unread":
        # Show unread emails
        await _show_unread_emails(update, gmail)
    elif args[0] == "auth":
        # Start authentication
        await _gmail_auth(update, gmail)
    elif args[0] == "code" and len(args) >= 2:
        # Complete authentication with code
        code = args[1]
        success = await gmail.complete_auth_with_code(code)
        if success:
            await update.message.reply_text("✅ Gmail authentication successful!")
        else:
            await update.message.reply_text("❌ Authentication failed. Please try again.")
    elif args[0] == "search" and len(args) >= 2:
        # Search emails
        query = " ".join(args[1:])
        await _search_emails(update, gmail, query)
    elif args[0] == "send" and len(args) >= 3:
        # Send email
        # Format: /gmail send <to> <subject> | <body>
        to = args[1]
        rest = " ".join(args[2:])
        if "|" in rest:
            subject, body = rest.split("|", 1)
        else:
            subject = rest
            body = ""
        await _send_email(update, gmail, to, subject.strip(), body.strip())
    elif args[0] == "labels":
        # List labels
        await _list_labels(update, gmail)
    else:
        await update.message.reply_text(
            "<b>Gmail</b>\n\n"
            "Usage:\n"
            "<code>/gmail</code> - Show recent emails\n"
            "<code>/gmail unread</code> - Show unread count\n"
            "<code>/gmail search &lt;query&gt;</code> - Search emails\n"
            "<code>/gmail send &lt;to&gt; &lt;subject&gt; | &lt;body&gt;</code> - Send email\n"
            "<code>/gmail labels</code> - List labels\n"
            "<code>/gmail auth</code> - Authenticate\n"
            "<code>/gmail code &lt;code&gt;</code> - Complete auth\n\n"
            "Example:\n"
            "<code>/gmail search from:example@gmail.com</code>\n"
            "<code>/gmail send user@example.com Hello | This is the body.</code>",
            parse_mode="HTML"
        )


async def _gmail_auth(update: Update, gmail) -> None:
    """Handle Gmail authentication."""
    if gmail.is_authenticated:
        await update.message.reply_text(f"Already authenticated as {gmail.user_email}")
        return
    
    auth_url = gmail.get_auth_url()
    if auth_url:
        await update.message.reply_text(
            "<b>Gmail Authentication</b>\n\n"
            "1. Click the link below to authenticate\n"
            "2. After approval, you'll be redirected to localhost\n"
            "3. Copy the <code>code</code> parameter from the URL\n"
            "4. Run <code>/gmail code YOUR_CODE</code>\n\n"
            f"<a href=\"{auth_url}\">Click here to authenticate</a>\n\n"
            "<i>Note: The redirect will fail (that's expected). "
            "Just copy the code from the URL.</i>",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        await update.message.reply_text(
            "Cannot generate auth URL.\n\n"
            "Please ensure data/google/credentials.json exists.\n"
            "Download from Google Cloud Console."
        )


async def _show_recent_emails(update: Update, gmail) -> None:
    """Show recent emails."""
    if not gmail.is_authenticated:
        success = await gmail.authenticate()
        if not success:
            await update.message.reply_text(
                "Not authenticated. Run `/gmail auth` first.",
                parse_mode="Markdown"
            )
            return
    
    emails = await gmail.list_emails(max_results=10)
    
    if not emails:
        await update.message.reply_text("No emails found.")
        return
    
    unread_count = await gmail.get_unread_count()
    
    text = f"**Recent Emails** ({unread_count} unread)\n\n"
    for email in emails:
        read_mark = "" if email.is_read else "🔵 "
        date_str = email.date.strftime("%m/%d %H:%M") if email.date else ""
        sender = email.sender.split("<")[0].strip()[:20]
        subject = email.subject[:40] + "..." if len(email.subject) > 40 else email.subject
        text += f"{read_mark}`{date_str}` **{sender}**\n{subject}\n\n"
    
    if len(text) > 4000:
        text = text[:4000] + "\n\n...(truncated)"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def _show_unread_emails(update: Update, gmail) -> None:
    """Show unread email count."""
    if not gmail.is_authenticated:
        success = await gmail.authenticate()
        if not success:
            await update.message.reply_text(
                "Not authenticated. Run `/gmail auth` first.",
                parse_mode="Markdown"
            )
            return
    
    unread_count = await gmail.get_unread_count()
    await update.message.reply_text(f"You have **{unread_count}** unread emails.", parse_mode="Markdown")


async def _search_emails(update: Update, gmail, query: str) -> None:
    """Search emails."""
    if not gmail.is_authenticated:
        success = await gmail.authenticate()
        if not success:
            await update.message.reply_text(
                "Not authenticated. Run `/gmail auth` first.",
                parse_mode="Markdown"
            )
            return
    
    emails = await gmail.search_emails(query, max_results=10)
    
    if not emails:
        await update.message.reply_text(f"No emails found for: `{query}`", parse_mode="Markdown")
        return
    
    text = f"**Search Results** ({len(emails)} found)\n\n"
    for email in emails:
        date_str = email.date.strftime("%Y-%m-%d") if email.date else ""
        sender = email.sender.split("<")[0].strip()[:20]
        subject = email.subject[:40] + "..." if len(email.subject) > 40 else email.subject
        text += f"`{date_str}` **{sender}**\n{subject}\n\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def _send_email(update: Update, gmail, to: str, subject: str, body: str) -> None:
    """Send an email."""
    if not gmail.is_authenticated:
        success = await gmail.authenticate()
        if not success:
            await update.message.reply_text(
                "Not authenticated. Run `/gmail auth` first.",
                parse_mode="Markdown"
            )
            return
    
    if not body:
        body = subject
        subject = "(No Subject)"
    
    message_id = await gmail.send_email(to=to, subject=subject, body=body)
    
    if message_id:
        await update.message.reply_text(
            f"**Email Sent**\n\n"
            f"To: {to}\n"
            f"Subject: {subject}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Failed to send email.")


async def _list_labels(update: Update, gmail) -> None:
    """List Gmail labels."""
    if not gmail.is_authenticated:
        success = await gmail.authenticate()
        if not success:
            await update.message.reply_text(
                "Not authenticated. Run `/gmail auth` first.",
                parse_mode="Markdown"
            )
            return
    
    labels = await gmail.list_labels()
    
    if not labels:
        await update.message.reply_text("No labels found.")
        return
    
    text = "**Gmail Labels**\n\n"
    for label in labels[:20]:
        unread = f" ({label.unread_count} unread)" if label.unread_count > 0 else ""
        text += f"• {label.name}{unread}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================
# Skills Registry Handlers
# ============================================

async def skills_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /skills_search command.
    
    Usage:
        /skills_search - List all available skills
        /skills_search <query> - Search for skills
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    registry = get_skills_registry()
    args = context.args or []
    
    query = " ".join(args) if args else ""
    
    # Search built-in and local first
    skills = await registry.search(query, limit=10)
    
    # Also search GitHub if query provided
    github_skills = []
    if query:
        msg = await update.message.reply_text(f"🔍 搜尋中: `{query}`...", parse_mode="Markdown")
        github_skills = await registry.search_github(query, limit=5)
        await msg.delete()
    
    # Combine results
    all_skills = skills + [s for s in github_skills if s.id not in [x.id for x in skills]]
    
    if not all_skills:
        await update.message.reply_text(
            f"❌ 找不到符合的技能: `{query}`\n\n"
            "💡 你也可以直接從 GitHub 安裝:\n"
            "`/skills_install github:owner/repo/path`\n\n"
            "或從 SkillsMP.com 複製 skill ID 安裝",
            parse_mode="Markdown"
        )
        return
    
    text = "**🎯 可用技能**\n\n" if not query else f"**🔍 搜尋結果: '{query}'**\n\n"
    
    # Show local/builtin skills
    local_skills = [s for s in all_skills if s.id in [x.id for x in skills]]
    if local_skills:
        text += "**📦 本地/內建:**\n"
        for skill in local_skills[:5]:
            installed = "✅ " if registry.is_installed(skill.id) else ""
            text += f"{installed}`{skill.id}`\n  _{skill.description[:50]}..._\n"
        text += "\n"
    
    # Show GitHub skills
    gh_skills = [s for s in all_skills if s in github_skills]
    if gh_skills:
        text += "**🐙 GitHub:**\n"
        for skill in gh_skills[:5]:
            text += f"`{skill.id}`\n  _{skill.description[:50]}..._\n"
        text += "\n"
    
    text += "**安裝方式:**\n"
    text += "• `/skills_install <skill_id>`\n"
    text += "• `/skills_install github:owner/repo/path`\n"
    text += "\n💡 更多技能: https://skillsmp.com"
    
    if len(text) > 4000:
        text = text[:4000] + "\n\n...(截斷)"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def skills_install_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /skills_install command.
    
    Usage:
        /skills_install <skill_id> - Install a skill
        /skills_install github:owner/repo/path - Install from GitHub
        /skills_install <skillsmp_id> - Install from SkillsMP
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("⚠️ 您沒有使用此機器人的權限。")
        return
    
    args = context.args or []
    
    if not args:
        await update.message.reply_text(
            "**📦 安裝技能**\n\n"
            "**用法:**\n"
            "`/skills_install <skill_id>`\n\n"
            "**支援格式:**\n"
            "• 內建技能 ID\n"
            "• GitHub: `github:owner/repo/path`\n"
            "• GitHub URL: `https://github.com/...`\n"
            "• SkillsMP ID: `owner-repo-path-skill-md`\n\n"
            "**範例:**\n"
            "`/skills_install web-search`\n"
            "`/skills_install github:vercel/next.js/.claude/skills`\n"
            "`/skills_install facebook-react-claude-skills-test-skill-md`\n\n"
            "💡 搜尋技能: `/skills_search <關鍵字>`\n"
            "💡 更多技能: https://skillsmp.com",
            parse_mode="Markdown"
        )
        return
    
    skill_id = " ".join(args)  # Support URLs with spaces
    registry = get_skills_registry()
    
    # Send processing message
    msg = await update.message.reply_text(f"📥 正在安裝 `{skill_id[:50]}...`", parse_mode="Markdown")
    
    success, message = await registry.install(skill_id)
    
    if success:
        await msg.edit_text(f"✅ {message}", parse_mode="Markdown")
    else:
        await msg.edit_text(f"❌ {message}", parse_mode="Markdown")


async def skills_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /skills_list command.
    
    Usage:
        /skills_list - List installed skills
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    registry = get_skills_registry()
    installed = registry.list_installed()
    
    if not installed:
        await update.message.reply_text(
            "No skills installed.\n\n"
            "Use `/skills_search` to find skills and `/skills_install` to install them.",
            parse_mode="Markdown"
        )
        return
    
    text = "**Installed Skills**\n\n"
    
    for skill in installed:
        enabled = "✅" if skill.enabled else "⬜"
        text += f"{enabled} **{skill.manifest.name}** v{skill.manifest.version}\n"
        text += f"_{skill.manifest.description[:50]}..._\n\n"
    
    stats = registry.get_stats()
    text += f"\nTotal: {stats['installed_count']} installed, {stats['enabled_count']} enabled"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def skills_uninstall_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /skills_uninstall command.
    
    Usage:
        /skills_uninstall <skill_id> - Uninstall a skill
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    args = context.args or []
    
    if not args:
        await update.message.reply_text(
            "**Uninstall Skill**\n\n"
            "Usage: `/skills_uninstall <skill_id>`\n\n"
            "Use `/skills_list` to see installed skills.",
            parse_mode="Markdown"
        )
        return
    
    skill_id = args[0]
    registry = get_skills_registry()
    
    success, message = await registry.uninstall(skill_id)
    
    if success:
        await update.message.reply_text(f"✅ {message}", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ {message}", parse_mode="Markdown")


def setup_google_handlers(app) -> None:
    """Setup Google and Skills Registry handlers."""
    from telegram.ext import CommandHandler
    
    # Calendar handlers
    app.add_handler(CommandHandler("calendar", calendar_command))
    
    # Gmail handlers
    app.add_handler(CommandHandler("gmail", gmail_command))
    
    # Skills Registry handlers
    app.add_handler(CommandHandler("skills_search", skills_search_command))
    app.add_handler(CommandHandler("skills_install", skills_install_command))
    app.add_handler(CommandHandler("skills_list", skills_list_command))
    app.add_handler(CommandHandler("skills_uninstall", skills_uninstall_command))
    
    logger.info("Google and Skills Registry handlers registered")


__all__ = [
    "calendar_command",
    "gmail_command",
    "skills_search_command",
    "skills_install_command",
    "skills_list_command",
    "skills_uninstall_command",
    "setup_google_handlers",
]

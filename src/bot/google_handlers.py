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
    Supports both Apple Calendar (macOS) and Google Calendar.
    
    Usage:
        /calendar - Show today's events
        /calendar week - Show this week's events
        /calendar list - List all calendars
        /calendar add <title> <time> - Add event
        /calendar auth - Start Google authentication
    """
    import html
    import platform
    
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    args = context.args or []
    
    # Check for Apple Calendar on macOS
    apple_calendar = None
    if platform.system() == "Darwin":
        try:
            from ..core.apple_calendar import get_apple_calendar
            apple_calendar = get_apple_calendar()
            if not apple_calendar.is_available():
                apple_calendar = None
        except Exception:
            apple_calendar = None
    
    # Get Google Calendar if available
    google_calendar = None
    if CALENDAR_AVAILABLE:
        google_calendar = get_calendar_manager()
    
    # Handle subcommands
    if not args:
        # Show today's events from all sources
        await _show_today_events_combined(update, apple_calendar, google_calendar)
    elif args[0] == "week":
        # Show this week's events from all sources
        await _show_week_events_combined(update, apple_calendar, google_calendar)
    elif args[0] == "auth":
        # Start Google Calendar authentication
        if google_calendar:
            await _calendar_auth(update, google_calendar)
        else:
            await update.message.reply_text("Google Calendar API 未安裝")
    elif args[0] == "code" and len(args) >= 2:
        # Complete Google authentication with code
        if google_calendar:
            code = args[1]
            success = await google_calendar.complete_auth_with_code(code)
            if success:
                await update.message.reply_text("✅ Google Calendar 認證成功!")
            else:
                await update.message.reply_text("❌ 認證失敗，請重試。")
        else:
            await update.message.reply_text("Google Calendar API 未安裝")
    elif args[0] == "add" and len(args) >= 3:
        # Add event (prefer Apple Calendar on macOS)
        title = args[1]
        time_str = " ".join(args[2:])
        await _add_event_combined(update, apple_calendar, google_calendar, title, time_str)
    elif args[0] == "list":
        # List calendars from all sources
        await _list_calendars_combined(update, apple_calendar, google_calendar)
    else:
        sources = []
        if apple_calendar:
            sources.append("Apple Calendar")
        if google_calendar:
            sources.append("Google Calendar")
        source_text = " + ".join(sources) if sources else "未設定"
        
        await update.message.reply_text(
            f"<b>📅 日曆管理</b>\n\n"
            f"來源: {source_text}\n\n"
            "<b>指令:</b>\n"
            "<code>/calendar</code> - 今日行程\n"
            "<code>/calendar week</code> - 本週行程\n"
            "<code>/calendar list</code> - 列出所有日曆\n"
            "<code>/calendar add &lt;標題&gt; &lt;時間&gt;</code> - 新增行程\n"
            "<code>/calendar auth</code> - Google 認證\n\n"
            "<b>範例:</b>\n"
            "<code>/calendar add 開會 2026-01-28T14:00</code>",
            parse_mode="HTML"
        )


async def _show_today_events_combined(update: Update, apple_calendar, google_calendar) -> None:
    """Show today's events from all calendar sources."""
    import html
    
    all_events = []
    sources = []
    
    # Get Apple Calendar events
    if apple_calendar:
        try:
            apple_events = apple_calendar.get_events_today()
            for event in apple_events:
                all_events.append({
                    "time": event.start_time,
                    "title": event.title,
                    "location": event.location,
                    "source": "Apple",
                })
            sources.append("Apple Calendar")
        except Exception as e:
            logger.warning(f"Failed to get Apple Calendar events: {e}")
    
    # Get Google Calendar events
    if google_calendar and google_calendar.is_authenticated:
        try:
            google_events = await google_calendar.get_events_today()
            for event in google_events:
                all_events.append({
                    "time": event.start,
                    "title": event.title,
                    "location": event.location,
                    "source": "Google",
                })
            sources.append("Google Calendar")
        except Exception as e:
            logger.warning(f"Failed to get Google Calendar events: {e}")
    
    if not sources:
        await update.message.reply_text(
            "未設定日曆來源。\n\n"
            "• macOS 用戶可直接使用 Apple Calendar\n"
            "• 使用 /calendar auth 設定 Google Calendar"
        )
        return
    
    if not all_events:
        await update.message.reply_text(f"📅 今日沒有行程\n\n來源: {', '.join(sources)}")
        return
    
    # Sort by time
    all_events.sort(key=lambda e: e["time"] if e["time"] else "00:00")
    
    text = f"<b>📅 今日行程</b>\n<i>來源: {', '.join(sources)}</i>\n\n"
    for event in all_events:
        time_obj = event["time"]
        if hasattr(time_obj, 'strftime'):
            time_str = time_obj.strftime("%H:%M")
        else:
            time_str = str(time_obj) if time_obj else "整天"
        title = html.escape(event["title"])
        text += f"• <code>{time_str}</code> - {title}\n"
        if event["location"]:
            location = html.escape(event["location"])
            text += f"  📍 {location}\n"
    
    await update.message.reply_text(text, parse_mode="HTML")


async def _show_week_events_combined(update: Update, apple_calendar, google_calendar) -> None:
    """Show this week's events from all calendar sources."""
    import html
    
    all_events = []
    sources = []
    
    # Get Apple Calendar events
    if apple_calendar:
        try:
            apple_events = apple_calendar.get_events_week()
            for event in apple_events:
                all_events.append({
                    "date": event.start_time.date() if event.start_time else None,
                    "time": event.start_time,
                    "title": event.title,
                    "source": "Apple",
                })
            sources.append("Apple Calendar")
        except Exception as e:
            logger.warning(f"Failed to get Apple Calendar events: {e}")
    
    # Get Google Calendar events
    if google_calendar and google_calendar.is_authenticated:
        try:
            google_events = await google_calendar.get_events_week()
            for event in google_events:
                all_events.append({
                    "date": event.start.date() if event.start else None,
                    "time": event.start,
                    "title": event.title,
                    "source": "Google",
                })
            sources.append("Google Calendar")
        except Exception as e:
            logger.warning(f"Failed to get Google Calendar events: {e}")
    
    if not sources:
        await update.message.reply_text(
            "未設定日曆來源。\n\n"
            "• macOS 用戶可直接使用 Apple Calendar\n"
            "• 使用 /calendar auth 設定 Google Calendar"
        )
        return
    
    if not all_events:
        await update.message.reply_text(f"📅 本週沒有行程\n\n來源: {', '.join(sources)}")
        return
    
    # Sort by date and time
    all_events.sort(key=lambda e: (e["date"] or "", e["time"] or ""))
    
    text = f"<b>📅 本週行程</b>\n<i>來源: {', '.join(sources)}</i>\n"
    current_date = None
    
    for event in all_events:
        if event["date"] != current_date:
            current_date = event["date"]
            if current_date:
                day_name = event["time"].strftime("%m/%d (%a)") if event["time"] else str(current_date)
                text += f"\n<b>{day_name}</b>\n"
        
        time_obj = event["time"]
        if hasattr(time_obj, 'strftime'):
            time_str = time_obj.strftime("%H:%M")
        else:
            time_str = "整天"
        title = html.escape(event["title"])
        text += f"• <code>{time_str}</code> - {title}\n"
    
    # Truncate if too long
    if len(text) > 4000:
        text = text[:4000] + "\n\n...(truncated)"
    
    await update.message.reply_text(text, parse_mode="HTML")


async def _list_calendars_combined(update: Update, apple_calendar, google_calendar) -> None:
    """List calendars from all sources."""
    import html
    
    text = "<b>📅 日曆列表</b>\n"
    has_calendars = False
    
    # List Apple Calendars
    if apple_calendar:
        try:
            apple_cals = apple_calendar.list_calendars()
            if apple_cals:
                has_calendars = True
                text += "\n<b>🍎 Apple Calendar</b>\n"
                for cal in apple_cals:
                    cal_name = html.escape(cal.name)
                    text += f"• {cal_name}\n"
        except Exception as e:
            logger.warning(f"Failed to list Apple calendars: {e}")
    
    # List Google Calendars
    if google_calendar:
        if google_calendar.is_authenticated:
            try:
                google_cals = await google_calendar.list_calendars()
                if google_cals:
                    has_calendars = True
                    text += "\n<b>📧 Google Calendar</b>\n"
                    for cal in google_cals:
                        cal_name = html.escape(cal.name)
                        primary = " ⭐" if cal.primary else ""
                        text += f"• {cal_name}{primary}\n"
            except Exception as e:
                logger.warning(f"Failed to list Google calendars: {e}")
        else:
            text += "\n<b>📧 Google Calendar</b>\n"
            text += "<i>未認證，使用 /calendar auth 設定</i>\n"
    
    if not has_calendars:
        text += "\n沒有找到日曆。\n"
        text += "\n• macOS 會自動使用 Apple Calendar\n"
        text += "• 使用 /calendar auth 連接 Google Calendar"
    
    await update.message.reply_text(text, parse_mode="HTML")


async def _add_event_combined(update: Update, apple_calendar, google_calendar, title: str, time_str: str) -> None:
    """Add event to calendar (prefers Apple Calendar on macOS)."""
    import html
    from datetime import datetime, timedelta
    
    try:
        start = datetime.fromisoformat(time_str)
        end = start + timedelta(hours=1)  # Default 1 hour duration
    except ValueError:
        await update.message.reply_text(
            "❌ 時間格式錯誤\n\n"
            "請使用 ISO 格式: YYYY-MM-DDTHH:MM\n"
            "例如: 2026-01-28T14:00"
        )
        return
    
    # Prefer Apple Calendar on macOS
    if apple_calendar:
        try:
            event_id = apple_calendar.create_event(
                title=title,
                start_time=start,
                end_time=end,
            )
            if event_id:
                title_escaped = html.escape(title)
                await update.message.reply_text(
                    f"<b>✅ 行程已建立</b>\n\n"
                    f"標題: {title_escaped}\n"
                    f"時間: {start.strftime('%Y-%m-%d %H:%M')}\n"
                    f"來源: Apple Calendar",
                    parse_mode="HTML"
                )
                return
        except Exception as e:
            logger.warning(f"Failed to create Apple Calendar event: {e}")
    
    # Fallback to Google Calendar
    if google_calendar and google_calendar.is_authenticated:
        try:
            event = await google_calendar.create_event(
                title=title,
                start=time_str,
            )
            if event:
                title_escaped = html.escape(event.title)
                await update.message.reply_text(
                    f"<b>✅ 行程已建立</b>\n\n"
                    f"標題: {title_escaped}\n"
                    f"時間: {event.start.strftime('%Y-%m-%d %H:%M')}\n"
                    f"來源: Google Calendar",
                    parse_mode="HTML"
                )
                return
        except Exception as e:
            logger.warning(f"Failed to create Google Calendar event: {e}")
    
    await update.message.reply_text("❌ 建立行程失敗，請確認日曆來源已設定")


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

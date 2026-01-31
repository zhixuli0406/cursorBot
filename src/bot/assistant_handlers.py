"""
Personal Assistant Handlers for CursorBot

Provides personal assistant features:
- /todo - Task management
- /reminder - Daily reminders
- /book - Booking assistant (flights, trains, hotels)
- /secretary - Secretary settings

These features work with the core scheduler and memory systems.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..utils.logger import logger
from ..utils.auth import is_authorized
from ..core.scheduler import get_scheduler, JobType
from ..core.memory import get_memory_manager


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ============================================
# Todo (Task Management)
# ============================================

async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /todo command - Task management.
    
    Usage:
        /todo - List all tasks
        /todo add <task> - Add a task
        /todo done <id> - Mark task as done
        /todo del <id> - Delete a task
        /todo clear - Clear completed tasks
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    memory = get_memory_manager()
    
    # Get user's todo list from memory
    todos_key = f"todos:{user_id}"
    todos = memory.get(todos_key) or []
    
    if not args:
        # List all tasks
        if not todos:
            await update.message.reply_text(
                "📝 <b>待辦事項</b>\n\n"
                "目前沒有待辦事項。\n\n"
                "使用 <code>/todo add &lt;任務&gt;</code> 新增任務。",
                parse_mode="HTML"
            )
            return
        
        text = "📝 <b>待辦事項</b>\n\n"
        for i, todo in enumerate(todos, 1):
            status = "✅" if todo.get("done") else "⬜"
            task = _escape_html(todo.get("task", ""))
            created = todo.get("created", "")[:10]
            text += f"{status} <b>{i}.</b> {task}\n"
            if todo.get("due"):
                text += f"   📅 {todo['due']}\n"
        
        text += (
            "\n<b>指令：</b>\n"
            "<code>/todo add &lt;任務&gt;</code> - 新增\n"
            "<code>/todo done &lt;編號&gt;</code> - 完成\n"
            "<code>/todo del &lt;編號&gt;</code> - 刪除\n"
            "<code>/todo clear</code> - 清除已完成"
        )
        
        await update.message.reply_text(text, parse_mode="HTML")
    
    elif args[0] == "add" and len(args) >= 2:
        # Add a task
        task_text = " ".join(args[1:])
        
        # Parse due date if specified (format: task @tomorrow, task @2026-01-30)
        due_date = None
        if "@" in task_text:
            parts = task_text.rsplit("@", 1)
            task_text = parts[0].strip()
            due_str = parts[1].strip().lower()
            
            if due_str == "today":
                due_date = datetime.now().strftime("%Y-%m-%d")
            elif due_str == "tomorrow":
                due_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            elif due_str.startswith("20"):  # Assume date format
                due_date = due_str[:10]
        
        new_todo = {
            "id": len(todos) + 1,
            "task": task_text,
            "done": False,
            "created": datetime.now().isoformat(),
            "due": due_date,
        }
        
        todos.append(new_todo)
        memory.set(todos_key, todos)
        
        text = f"✅ 已新增任務：<b>{_escape_html(task_text)}</b>"
        if due_date:
            text += f"\n📅 截止日期：{due_date}"
        
        await update.message.reply_text(text, parse_mode="HTML")
    
    elif args[0] == "done" and len(args) >= 2:
        # Mark task as done
        try:
            task_num = int(args[1])
            if 1 <= task_num <= len(todos):
                todos[task_num - 1]["done"] = True
                todos[task_num - 1]["completed_at"] = datetime.now().isoformat()
                memory.set(todos_key, todos)
                
                task_text = todos[task_num - 1].get("task", "")
                await update.message.reply_text(
                    f"✅ 已完成：<b>{_escape_html(task_text)}</b>",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ 無效的任務編號")
        except ValueError:
            await update.message.reply_text("❌ 請輸入有效的任務編號")
    
    elif args[0] == "del" and len(args) >= 2:
        # Delete a task
        try:
            task_num = int(args[1])
            if 1 <= task_num <= len(todos):
                removed = todos.pop(task_num - 1)
                memory.set(todos_key, todos)
                
                await update.message.reply_text(
                    f"🗑️ 已刪除：<b>{_escape_html(removed.get('task', ''))}</b>",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ 無效的任務編號")
        except ValueError:
            await update.message.reply_text("❌ 請輸入有效的任務編號")
    
    elif args[0] == "clear":
        # Clear completed tasks
        before_count = len(todos)
        todos = [t for t in todos if not t.get("done")]
        cleared = before_count - len(todos)
        memory.set(todos_key, todos)
        
        await update.message.reply_text(f"🧹 已清除 {cleared} 個已完成的任務")
    
    elif args[0] == "undone" and len(args) >= 2:
        # Mark task as not done
        try:
            task_num = int(args[1])
            if 1 <= task_num <= len(todos):
                todos[task_num - 1]["done"] = False
                if "completed_at" in todos[task_num - 1]:
                    del todos[task_num - 1]["completed_at"]
                memory.set(todos_key, todos)
                
                await update.message.reply_text("↩️ 已取消完成狀態")
            else:
                await update.message.reply_text("❌ 無效的任務編號")
        except ValueError:
            await update.message.reply_text("❌ 請輸入有效的任務編號")
    
    else:
        await update.message.reply_text(
            "📝 <b>待辦事項</b>\n\n"
            "Usage:\n"
            "<code>/todo</code> - 列出所有任務\n"
            "<code>/todo add &lt;任務&gt;</code> - 新增任務\n"
            "<code>/todo add 任務 @tomorrow</code> - 新增含截止日\n"
            "<code>/todo done &lt;編號&gt;</code> - 標記完成\n"
            "<code>/todo undone &lt;編號&gt;</code> - 取消完成\n"
            "<code>/todo del &lt;編號&gt;</code> - 刪除任務\n"
            "<code>/todo clear</code> - 清除已完成",
            parse_mode="HTML"
        )


# ============================================
# Reminder
# ============================================

async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /reminder command - Daily reminders.
    
    Usage:
        /reminder - Show reminder settings
        /reminder on - Enable daily reminder
        /reminder off - Disable daily reminder
        /reminder time <HH:MM> - Set reminder time
        /reminder add <message> - Add a reminder message
    """
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    memory = get_memory_manager()
    scheduler = get_scheduler()
    
    # Get user's reminder settings
    reminder_key = f"reminder:{user_id}"
    settings = memory.get(reminder_key) or {
        "enabled": False,
        "time": "09:00",
        "messages": [],
        "include_todos": True,
        "include_calendar": True,
    }
    
    if not args:
        # Show current settings
        status = "🟢 啟用" if settings.get("enabled") else "🔴 停用"
        time_str = settings.get("time", "09:00")
        
        text = (
            "⏰ <b>每日提醒設定</b>\n\n"
            f"狀態：{status}\n"
            f"時間：{time_str}\n"
            f"包含待辦事項：{'是' if settings.get('include_todos') else '否'}\n"
            f"包含行事曆：{'是' if settings.get('include_calendar') else '否'}\n"
        )
        
        messages = settings.get("messages", [])
        if messages:
            text += "\n<b>自訂提醒：</b>\n"
            for i, msg in enumerate(messages, 1):
                text += f"{i}. {_escape_html(msg)}\n"
        
        text += (
            "\n<b>指令：</b>\n"
            "<code>/reminder on</code> - 啟用\n"
            "<code>/reminder off</code> - 停用\n"
            "<code>/reminder time 08:30</code> - 設定時間\n"
            "<code>/reminder add &lt;訊息&gt;</code> - 新增提醒\n"
            "<code>/reminder del &lt;編號&gt;</code> - 刪除提醒"
        )
        
        await update.message.reply_text(text, parse_mode="HTML")
    
    elif args[0] == "on":
        settings["enabled"] = True
        memory.set(reminder_key, settings)
        
        # Schedule the daily reminder
        await _schedule_daily_reminder(user_id, chat_id, settings, scheduler, context)
        
        await update.message.reply_text(
            f"✅ 每日提醒已啟用\n\n"
            f"每天 {settings.get('time', '09:00')} 會收到提醒。"
        )
    
    elif args[0] == "off":
        settings["enabled"] = False
        memory.set(reminder_key, settings)
        
        # Cancel scheduled reminder
        job_id = f"reminder:{user_id}"
        scheduler.cancel(job_id)
        
        await update.message.reply_text("🔴 每日提醒已停用")
    
    elif args[0] == "time" and len(args) >= 2:
        time_str = args[1]
        
        # Validate time format
        try:
            datetime.strptime(time_str, "%H:%M")
            settings["time"] = time_str
            memory.set(reminder_key, settings)
            
            # Reschedule if enabled
            if settings.get("enabled"):
                await _schedule_daily_reminder(user_id, chat_id, settings, scheduler, context)
            
            await update.message.reply_text(f"✅ 提醒時間已設定為 {time_str}")
        except ValueError:
            await update.message.reply_text("❌ 無效的時間格式，請使用 HH:MM（例如 09:00）")
    
    elif args[0] == "add" and len(args) >= 2:
        message = " ".join(args[1:])
        messages = settings.get("messages", [])
        messages.append(message)
        settings["messages"] = messages
        memory.set(reminder_key, settings)
        
        await update.message.reply_text(f"✅ 已新增提醒：{_escape_html(message)}", parse_mode="HTML")
    
    elif args[0] == "del" and len(args) >= 2:
        try:
            idx = int(args[1])
            messages = settings.get("messages", [])
            if 1 <= idx <= len(messages):
                removed = messages.pop(idx - 1)
                settings["messages"] = messages
                memory.set(reminder_key, settings)
                await update.message.reply_text(f"🗑️ 已刪除提醒：{_escape_html(removed)}", parse_mode="HTML")
            else:
                await update.message.reply_text("❌ 無效的編號")
        except ValueError:
            await update.message.reply_text("❌ 請輸入有效的編號")
    
    else:
        await update.message.reply_text(
            "Usage:\n"
            "<code>/reminder</code> - 查看設定\n"
            "<code>/reminder on/off</code> - 啟用/停用\n"
            "<code>/reminder time HH:MM</code> - 設定時間\n"
            "<code>/reminder add &lt;訊息&gt;</code> - 新增提醒",
            parse_mode="HTML"
        )


async def _schedule_daily_reminder(user_id: str, chat_id: int, settings: dict, scheduler, context) -> None:
    """Schedule or reschedule daily reminder."""
    job_id = f"reminder:{user_id}"
    
    # Cancel existing job
    scheduler.cancel(job_id)
    
    if not settings.get("enabled"):
        return
    
    # Parse time
    time_str = settings.get("time", "09:00")
    hour, minute = map(int, time_str.split(":"))
    
    # Calculate next run time
    now = datetime.now()
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    
    # Schedule job
    async def send_reminder():
        await _send_daily_reminder(user_id, chat_id, settings, context)
    
    scheduler.schedule_once(
        job_id=job_id,
        name=f"Daily reminder for {user_id}",
        callback=send_reminder,
        run_at=next_run,
        user_id=int(user_id),
        chat_id=chat_id,
    )


async def _send_daily_reminder(user_id: str, chat_id: int, settings: dict, context) -> None:
    """Send daily reminder message."""
    memory = get_memory_manager()
    
    text = "☀️ <b>早安！這是你的每日提醒</b>\n\n"
    
    # Include todos if enabled
    if settings.get("include_todos", True):
        todos_key = f"todos:{user_id}"
        todos = memory.get(todos_key) or []
        pending_todos = [t for t in todos if not t.get("done")]
        
        if pending_todos:
            text += "📝 <b>待辦事項：</b>\n"
            for i, todo in enumerate(pending_todos[:5], 1):
                text += f"  {i}. {_escape_html(todo.get('task', ''))}\n"
            if len(pending_todos) > 5:
                text += f"  ...還有 {len(pending_todos) - 5} 項\n"
            text += "\n"
    
    # Include custom messages
    messages = settings.get("messages", [])
    if messages:
        text += "💡 <b>提醒事項：</b>\n"
        for msg in messages:
            text += f"  • {_escape_html(msg)}\n"
        text += "\n"
    
    text += "祝你有美好的一天！🌟"
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
        )
        
        # Reschedule for tomorrow
        scheduler = get_scheduler()
        await _schedule_daily_reminder(user_id, chat_id, settings, scheduler, context)
        
    except Exception as e:
        logger.error(f"Failed to send reminder to {user_id}: {e}")


# ============================================
# Booking Assistant
# ============================================

async def book_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /book command - Booking assistant.
    
    Usage:
        /book - Show booking options
        /book flight <from> <to> <date> - Search flights
        /book train <from> <to> <date> - Search trains
        /book hotel <city> <checkin> <checkout> - Search hotels
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    if not args:
        # Show booking options
        keyboard = [
            [
                InlineKeyboardButton("✈️ 機票", callback_data="book:flight"),
                InlineKeyboardButton("🚄 火車", callback_data="book:train"),
            ],
            [
                InlineKeyboardButton("🏨 飯店", callback_data="book:hotel"),
                InlineKeyboardButton("🚗 租車", callback_data="book:car"),
            ],
        ]
        
        await update.message.reply_text(
            "🎫 <b>訂票助手</b>\n\n"
            "我可以幫你搜尋並比較各種訂票資訊。\n\n"
            "請選擇要預訂的類型：",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    
    elif args[0] == "flight":
        if len(args) >= 4:
            origin = args[1].upper()
            dest = args[2].upper()
            date = args[3]
            
            await update.message.reply_text(
                f"✈️ <b>搜尋機票</b>\n\n"
                f"出發地：{_escape_html(origin)}\n"
                f"目的地：{_escape_html(dest)}\n"
                f"日期：{_escape_html(date)}\n\n"
                f"正在搜尋最佳票價...\n\n"
                f"<i>提示：你可以使用以下網站比價：</i>\n"
                f"• <a href='https://www.google.com/travel/flights?q={origin}+to+{dest}'>Google Flights</a>\n"
                f"• <a href='https://www.skyscanner.com'>Skyscanner</a>\n"
                f"• <a href='https://www.kayak.com'>Kayak</a>",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            await update.message.reply_text(
                "✈️ <b>搜尋機票</b>\n\n"
                "用法：<code>/book flight &lt;出發地&gt; &lt;目的地&gt; &lt;日期&gt;</code>\n\n"
                "範例：\n"
                "<code>/book flight TPE NRT 2026-02-15</code>\n"
                "<code>/book flight 台北 東京 2026-02-15</code>",
                parse_mode="HTML"
            )
    
    elif args[0] == "train":
        if len(args) >= 4:
            origin = args[1]
            dest = args[2]
            date = args[3]
            
            await update.message.reply_text(
                f"🚄 <b>搜尋火車票</b>\n\n"
                f"出發站：{_escape_html(origin)}\n"
                f"目的站：{_escape_html(dest)}\n"
                f"日期：{_escape_html(date)}\n\n"
                f"<i>提示：你可以使用以下網站訂票：</i>\n"
                f"• <a href='https://www.thsrc.com.tw'>台灣高鐵</a>\n"
                f"• <a href='https://www.railway.gov.tw'>台鐵</a>\n"
                f"• <a href='https://www.jreast.co.jp'>JR 東日本</a>",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            await update.message.reply_text(
                "🚄 <b>搜尋火車票</b>\n\n"
                "用法：<code>/book train &lt;出發站&gt; &lt;目的站&gt; &lt;日期&gt;</code>\n\n"
                "範例：\n"
                "<code>/book train 台北 高雄 2026-02-15</code>",
                parse_mode="HTML"
            )
    
    elif args[0] == "hotel":
        if len(args) >= 4:
            city = args[1]
            checkin = args[2]
            checkout = args[3]
            
            await update.message.reply_text(
                f"🏨 <b>搜尋飯店</b>\n\n"
                f"城市：{_escape_html(city)}\n"
                f"入住：{_escape_html(checkin)}\n"
                f"退房：{_escape_html(checkout)}\n\n"
                f"<i>提示：你可以使用以下網站比價：</i>\n"
                f"• <a href='https://www.booking.com'>Booking.com</a>\n"
                f"• <a href='https://www.agoda.com'>Agoda</a>\n"
                f"• <a href='https://www.hotels.com'>Hotels.com</a>\n"
                f"• <a href='https://www.trivago.com'>Trivago</a>",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            await update.message.reply_text(
                "🏨 <b>搜尋飯店</b>\n\n"
                "用法：<code>/book hotel &lt;城市&gt; &lt;入住日&gt; &lt;退房日&gt;</code>\n\n"
                "範例：\n"
                "<code>/book hotel 東京 2026-02-15 2026-02-18</code>",
                parse_mode="HTML"
            )
    
    else:
        await update.message.reply_text(
            "🎫 <b>訂票助手</b>\n\n"
            "用法：\n"
            "<code>/book</code> - 顯示選項\n"
            "<code>/book flight &lt;出發&gt; &lt;目的&gt; &lt;日期&gt;</code>\n"
            "<code>/book train &lt;出發&gt; &lt;目的&gt; &lt;日期&gt;</code>\n"
            "<code>/book hotel &lt;城市&gt; &lt;入住&gt; &lt;退房&gt;</code>",
            parse_mode="HTML"
        )


async def book_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle booking button callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "book:flight":
        await query.message.reply_text(
            "✈️ <b>搜尋機票</b>\n\n"
            "請輸入：\n"
            "<code>/book flight 出發地 目的地 日期</code>\n\n"
            "範例：\n"
            "<code>/book flight TPE NRT 2026-02-15</code>",
            parse_mode="HTML"
        )
    elif data == "book:train":
        await query.message.reply_text(
            "🚄 <b>搜尋火車票</b>\n\n"
            "請輸入：\n"
            "<code>/book train 出發站 目的站 日期</code>\n\n"
            "範例：\n"
            "<code>/book train 台北 高雄 2026-02-15</code>",
            parse_mode="HTML"
        )
    elif data == "book:hotel":
        await query.message.reply_text(
            "🏨 <b>搜尋飯店</b>\n\n"
            "請輸入：\n"
            "<code>/book hotel 城市 入住日 退房日</code>\n\n"
            "範例：\n"
            "<code>/book hotel 東京 2026-02-15 2026-02-18</code>",
            parse_mode="HTML"
        )
    elif data == "book:car":
        await query.message.reply_text(
            "🚗 <b>租車</b>\n\n"
            "<i>提示：你可以使用以下網站租車：</i>\n"
            "• <a href='https://www.rentalcars.com'>RentalCars</a>\n"
            "• <a href='https://www.hertz.com'>Hertz</a>\n"
            "• <a href='https://www.avis.com'>Avis</a>",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


# ============================================
# Secretary Settings
# ============================================

async def secretary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /secretary command - Personal secretary settings.
    
    Usage:
        /secretary - Show settings
        /secretary name <name> - Set secretary name
        /secretary style <style> - Set response style
        /secretary summary on/off - Enable/disable daily summaries
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    memory = get_memory_manager()
    
    # Get user's secretary settings
    secretary_key = f"secretary:{user_id}"
    settings = memory.get(secretary_key) or {
        "name": "小秘書",
        "style": "friendly",
        "daily_summary": True,
        "proactive_suggestions": True,
        "language": "zh-TW",
    }
    
    # All available styles
    style_names = {
        "friendly": "親切友善",
        "professional": "專業正式",
        "casual": "輕鬆隨意",
        "brief": "簡潔扼要",
        "humorous": "幽默風趣",
        "motivational": "激勵鼓舞",
        "technical": "技術專業",
        "empathetic": "同理關懷",
        "creative": "創意發想",
        "witty": "機智俏皮",
        "warm": "溫暖體貼",
    }
    
    if not args:
        # Show current settings
        current_style = settings.get('style', 'friendly')
        
        text = (
            "👩‍💼 <b>秘書設定</b>\n\n"
            f"名稱：{_escape_html(settings.get('name', '小秘書'))}\n"
            f"風格：{style_names.get(current_style, '親切友善')}\n"
            f"每日摘要：{'是' if settings.get('daily_summary') else '否'}\n"
            f"主動建議：{'是' if settings.get('proactive_suggestions') else '否'}\n"
            f"語言：{settings.get('language', 'zh-TW')}\n"
        )
        
        text += (
            "\n<b>指令：</b>\n"
            "<code>/secretary name &lt;名稱&gt;</code> - 設定名稱\n"
            "<code>/secretary style &lt;風格&gt;</code> - 設定風格\n"
            "<code>/secretary summary on/off</code> - 每日摘要\n"
            "<code>/secretary suggestions on/off</code> - 主動建議\n"
            "\n<b>風格選項：</b>\n"
            "friendly（親切）、professional（專業）\n"
            "casual（輕鬆）、brief（簡潔）\n"
            "humorous（幽默）、motivational（激勵）\n"
            "technical（技術）、empathetic（同理）\n"
            "creative（創意）、witty（機智）、warm（溫暖）"
        )
        
        await update.message.reply_text(text, parse_mode="HTML")
    
    elif args[0] == "name" and len(args) >= 2:
        name = " ".join(args[1:])
        settings["name"] = name
        memory.set(secretary_key, settings)
        await update.message.reply_text(f"✅ 秘書名稱已設為：{_escape_html(name)}", parse_mode="HTML")
    
    elif args[0] == "style" and len(args) >= 2:
        style = args[1].lower()
        
        if style in style_names:
            settings["style"] = style
            memory.set(secretary_key, settings)
            await update.message.reply_text(f"✅ 回應風格已設為：{style_names[style]}")
        else:
            await update.message.reply_text(
                f"❌ 無效的風格。\n\n可選：\n{', '.join(style_names.keys())}"
            )
    
    elif args[0] == "summary" and len(args) >= 2:
        enabled = args[1].lower() in ("on", "true", "yes", "1")
        settings["daily_summary"] = enabled
        memory.set(secretary_key, settings)
        
        status = "啟用" if enabled else "停用"
        await update.message.reply_text(f"✅ 每日摘要已{status}")
    
    elif args[0] == "suggestions" and len(args) >= 2:
        enabled = args[1].lower() in ("on", "true", "yes", "1")
        settings["proactive_suggestions"] = enabled
        memory.set(secretary_key, settings)
        
        status = "啟用" if enabled else "停用"
        await update.message.reply_text(f"✅ 主動建議已{status}")
    
    else:
        await update.message.reply_text(
            "👩‍💼 <b>秘書設定</b>\n\n"
            "用法：\n"
            "<code>/secretary</code> - 查看設定\n"
            "<code>/secretary name &lt;名稱&gt;</code>\n"
            "<code>/secretary style &lt;風格&gt;</code>\n"
            "<code>/secretary summary on/off</code>\n"
            "<code>/secretary suggestions on/off</code>",
            parse_mode="HTML"
        )


# ============================================
# Handler Registration
# ============================================

def setup_assistant_handlers(app) -> None:
    """Register personal assistant handlers."""
    # Todo
    app.add_handler(CommandHandler("todo", todo_command))
    app.add_handler(CommandHandler("todos", todo_command))
    app.add_handler(CommandHandler("task", todo_command))
    app.add_handler(CommandHandler("tasks", todo_command))
    
    # Reminder
    app.add_handler(CommandHandler("reminder", reminder_command))
    app.add_handler(CommandHandler("remind", reminder_command))
    
    # Booking
    app.add_handler(CommandHandler("book", book_command))
    app.add_handler(CommandHandler("booking", book_command))
    app.add_handler(CallbackQueryHandler(book_callback, pattern="^book:"))
    
    # Secretary
    app.add_handler(CommandHandler("secretary", secretary_command))
    app.add_handler(CommandHandler("assistant", secretary_command))
    
    logger.info("Personal assistant handlers registered")


__all__ = [
    "todo_command",
    "reminder_command",
    "book_command",
    "secretary_command",
    "setup_assistant_handlers",
]

"""
Core feature handlers for Telegram Bot
Integrates memory, skills, approvals, and other core features
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from ..core import (
    get_memory_manager,
    get_skill_manager,
    get_context_manager,
    get_scheduler,
    get_approval_manager,
    ApprovalType,
)
from ..utils.auth import authorized_only
from ..utils.logger import logger


# ============================================
# Memory Commands
# ============================================


@authorized_only
async def memory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /memory command.
    List, add, or search memories.

    Usage:
        /memory - List memories
        /memory add <key> <value> - Add memory
        /memory get <key> - Get memory
        /memory del <key> - Delete memory
        /memory search <query> - Search memories
    """
    user_id = update.effective_user.id
    args = context.args or []
    memory = get_memory_manager()

    if not args:
        # List memories
        memories = await memory.list_memories(user_id, limit=10)

        if not memories:
            await update.message.reply_text(
                "🧠 <b>記憶系統</b>\n\n"
                "目前沒有儲存任何記憶。\n\n"
                "<b>用法:</b>\n"
                "• <code>/memory add key value</code> - 新增記憶\n"
                "• <code>/memory get key</code> - 取得記憶\n"
                "• <code>/memory del key</code> - 刪除記憶\n"
                "• <code>/memory search query</code> - 搜尋",
                parse_mode="HTML",
            )
            return

        text = "🧠 <b>我的記憶</b>\n\n"
        for m in memories:
            value = m['value'][:50] + "..." if len(m['value']) > 50 else m['value']
            text += f"• <code>{m['key']}</code>: {value}\n"

        await update.message.reply_text(text, parse_mode="HTML")

    elif args[0] == "add" and len(args) >= 3:
        key = args[1]
        value = " ".join(args[2:])
        await memory.remember(user_id, key, value)
        await update.message.reply_text(
            f"✅ 已記住: <code>{key}</code>",
            parse_mode="HTML",
        )

    elif args[0] == "get" and len(args) >= 2:
        key = args[1]
        value = await memory.recall(user_id, key)
        if value:
            await update.message.reply_text(
                f"🧠 <code>{key}</code>:\n{value}",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(f"❌ 找不到記憶: {key}")

    elif args[0] == "del" and len(args) >= 2:
        key = args[1]
        deleted = await memory.forget(user_id, key)
        if deleted:
            await update.message.reply_text(f"✅ 已刪除: {key}")
        else:
            await update.message.reply_text(f"❌ 找不到記憶: {key}")

    elif args[0] == "search" and len(args) >= 2:
        query = " ".join(args[1:])
        results = await memory.search_memories(user_id, query)

        if not results:
            await update.message.reply_text(f"❌ 找不到符合的記憶: {query}")
            return

        text = f"🔍 <b>搜尋結果:</b> {query}\n\n"
        for m in results:
            value = m['value'][:50] + "..." if len(m['value']) > 50 else m['value']
            text += f"• <code>{m['key']}</code>: {value}\n"

        await update.message.reply_text(text, parse_mode="HTML")

    else:
        await update.message.reply_text(
            "❌ 無效的記憶指令。使用 /memory 查看用法。"
        )


# ============================================
# Skills Commands
# ============================================


@authorized_only
async def skills_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /skills command.
    List available skills (both command and agent skills).
    """
    skills = get_skill_manager()

    # Load built-in skills if not loaded
    if not skills.list_skills():
        await skills.load_builtin_skills()

    args = context.args if context.args else []
    
    # /skills agent - show agent skills
    if args and args[0] == "agent":
        agent_skills = skills.list_agent_skills()
        
        if not agent_skills:
            await update.message.reply_text("❌ 沒有可用的 Agent 技能")
            return
        
        text = "🤖 <b>Agent 技能</b>\n\n"
        text += "這些技能可在 /agent 指令中使用:\n\n"
        
        for skill in agent_skills:
            status = "✅" if skill.enabled else "❌"
            text += f"{status} <b>{skill.name}</b>\n"
            text += f"   {skill.description}\n"
            if skill.categories:
                text += f"   分類: {', '.join(skill.categories)}\n"
            if skill.examples:
                text += f"   範例: {skill.examples[0]}\n"
            text += "\n"
        
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    # Default: show command skills
    skill_list = skills.list_skills()
    agent_skills = skills.list_agent_skills()

    text = "🎯 <b>可用技能</b>\n\n"
    
    # Command skills
    if skill_list:
        text += "<b>📋 指令技能:</b>\n"
        for skill in skill_list:
            status = "✅" if skill.enabled else "❌"
            commands = ", ".join([f"/{c}" for c in skill.commands])
            text += f"{status} <b>{skill.name}</b>: {commands}\n"
        text += "\n"
    
    # Agent skills summary
    if agent_skills:
        text += f"<b>🤖 Agent 技能:</b> {len(agent_skills)} 個可用\n"
        text += "使用 <code>/skills agent</code> 查看詳情\n\n"
    
    text += "<b>使用說明:</b>\n"
    text += "• 指令技能: 直接使用 /指令 執行\n"
    text += "• Agent 技能: 透過 /agent 指令使用\n"

    await update.message.reply_text(text, parse_mode="HTML")


@authorized_only
async def skill_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle skill commands.
    Routes to appropriate skill based on command.
    """
    message = update.message.text
    if not message.startswith("/"):
        return

    # Extract command and args
    parts = message.split()
    command = parts[0][1:]  # Remove /
    args = parts[1:] if len(parts) > 1 else []

    skills = get_skill_manager()

    # Load built-in skills if not loaded
    if not skills.list_skills():
        await skills.load_builtin_skills()

    # Try to execute skill command
    handled = await skills.execute_command(update, context, command, args)

    if not handled:
        # Not a skill command, let other handlers process it
        pass


# ============================================
# Scheduler Commands
# ============================================


@authorized_only
async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /schedule command.
    List or manage scheduled jobs.

    Usage:
        /schedule - List jobs
        /schedule cancel <job_id> - Cancel job
    """
    user_id = update.effective_user.id
    args = context.args or []
    scheduler = get_scheduler()

    if not args:
        # List jobs
        jobs = scheduler.list_jobs(user_id)

        if not jobs:
            await update.message.reply_text(
                "⏰ <b>排程系統</b>\n\n"
                "目前沒有排程任務。\n\n"
                "使用 /remind 設定提醒，或透過技能建立排程任務。",
                parse_mode="HTML",
            )
            return

        text = "⏰ <b>我的排程</b>\n\n"
        for job in jobs:
            status_emoji = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
            }.get(job.status.value, "❓")

            next_run = job.next_run.strftime("%H:%M:%S") if job.next_run else "N/A"
            text += f"{status_emoji} <code>{job.job_id[:8]}</code>: {job.name}\n"
            text += f"   下次執行: {next_run}\n\n"

        await update.message.reply_text(text, parse_mode="HTML")

    elif args[0] == "cancel" and len(args) >= 2:
        job_id = args[1]

        # Find job by prefix
        jobs = scheduler.list_jobs(user_id)
        matching = [j for j in jobs if j.job_id.startswith(job_id)]

        if not matching:
            await update.message.reply_text(f"❌ 找不到排程: {job_id}")
            return

        scheduler.cancel_job(matching[0].job_id)
        await update.message.reply_text(f"✅ 已取消排程: {matching[0].name}")

    else:
        await update.message.reply_text(
            "❌ 無效的排程指令。使用 /schedule 查看用法。"
        )


# ============================================
# Context Commands
# ============================================


@authorized_only
async def clear_context_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /clear command.
    Clear conversation context.
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    ctx_manager = get_context_manager()

    ctx_manager.clear_context(user_id, chat_id)

    await update.message.reply_text(
        "🗑️ <b>已清除對話上下文</b>\n\n"
        "Bot 將不會記住之前的對話內容。",
        parse_mode="HTML",
    )


# ============================================
# Stats Commands
# ============================================


@authorized_only
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /stats command.
    Show user statistics.
    """
    user_id = update.effective_user.id
    memory = get_memory_manager()
    ctx_manager = get_context_manager()
    scheduler = get_scheduler()

    # Get task stats
    task_stats = await memory.get_task_stats(user_id)

    # Get context stats
    ctx_stats = ctx_manager.get_stats()

    # Get scheduler stats
    sched_stats = scheduler.get_stats()

    text = "📊 <b>使用統計</b>\n\n"

    text += "<b>任務統計:</b>\n"
    text += f"• 總任務數: {task_stats['total_tasks']}\n"
    text += f"• 完成任務: {task_stats['completed_tasks']}\n"
    text += f"• 失敗任務: {task_stats['failed_tasks']}\n"

    success_rate = (
        task_stats['completed_tasks'] / task_stats['total_tasks'] * 100
        if task_stats['total_tasks'] > 0 else 0
    )
    text += f"• 成功率: {success_rate:.1f}%\n\n"

    text += "<b>系統狀態:</b>\n"
    text += f"• 活躍對話: {ctx_stats['active_contexts']}\n"
    text += f"• 排程任務: {sched_stats['pending']}\n"
    text += f"• 排程器: {'運行中' if sched_stats['scheduler_running'] else '已停止'}\n"

    await update.message.reply_text(text, parse_mode="HTML")


# ============================================
# Settings Commands
# ============================================


@authorized_only
async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /settings command.
    Show and manage user settings.
    """
    user_id = update.effective_user.id
    args = context.args or []
    memory = get_memory_manager()

    prefs = await memory.get_user_preferences(user_id)

    if not args:
        # Show settings
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 通知", callback_data="settings_notifications")],
            [InlineKeyboardButton("📝 自訂提示詞", callback_data="settings_prompt")],
            [InlineKeyboardButton("📁 預設倉庫", callback_data="settings_repo")],
        ])

        text = "⚙️ <b>設定</b>\n\n"
        text += f"<b>通知:</b> {'開啟' if prefs.get('notifications_enabled') else '關閉'}\n"
        text += f"<b>預設倉庫:</b> {prefs.get('default_repo') or '未設定'}\n"
        text += f"<b>自訂提示詞:</b> {'已設定' if prefs.get('custom_prompt') else '未設定'}\n"

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    elif args[0] == "notifications":
        current = prefs.get('notifications_enabled', True)
        new_value = not current
        await memory.set_user_preference(user_id, 'notifications_enabled', int(new_value))
        await update.message.reply_text(
            f"✅ 通知已{'開啟' if new_value else '關閉'}"
        )

    elif args[0] == "prompt" and len(args) >= 2:
        prompt = " ".join(args[1:])
        await memory.set_user_preference(user_id, 'custom_prompt', prompt)
        await update.message.reply_text(
            f"✅ 自訂提示詞已設定:\n{prompt[:100]}..."
        )

    else:
        await update.message.reply_text(
            "❌ 無效的設定指令。使用 /settings 查看設定。"
        )


@authorized_only
async def agent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /agent command - Run Agent Loop for complex tasks.
    
    Usage: /agent <task description>
    """
    if not context.args:
        await update.message.reply_text(
            "🤖 <b>Agent Loop</b>\n\n"
            "使用方式: <code>/agent &lt;任務描述&gt;</code>\n\n"
            "範例:\n"
            "• <code>/agent 幫我分析這段程式碼的效能問題</code>\n"
            "• <code>/agent 建立一個完整的登入系統</code>\n"
            "• <code>/agent 重構這個模組並加入測試</code>\n\n"
            "切換模型: <code>/model set &lt;provider&gt;</code>",
            parse_mode="HTML",
        )
        return
    
    task = " ".join(context.args)
    user_id = str(update.effective_user.id)
    
    # Get current model info
    from ..core.llm_providers import get_llm_manager
    manager = get_llm_manager()
    current_model = manager.get_user_model(user_id)
    model_info = f"{current_model[0]}/{current_model[1]}" if current_model else "未設定"
    
    status_msg = await update.message.reply_text(
        f"🤖 <b>Agent Loop 啟動中...</b>\n\n"
        f"任務: {task[:100]}{'...' if len(task) > 100 else ''}\n"
        f"模型: <code>{model_info}</code>\n\n"
        f"⏳ Agent 正在分析任務...",
        parse_mode="HTML",
    )
    
    try:
        from ..core import get_agent_loop, AgentLoop
        from ..core.llm_providers import get_llm_manager
        import uuid
        
        # Get user's selected provider function
        manager = get_llm_manager()
        user_provider = manager.get_llm_provider_function_for_user(user_id)
        
        # Create agent with user's provider
        agent = get_agent_loop()
        
        # Temporarily use user's provider if set
        original_provider = agent.llm_provider
        if user_provider:
            agent.llm_provider = user_provider
        
        # Run the agent loop
        result = await agent.run(
            prompt=task,
            user_id=user_id,
            session_id=str(uuid.uuid4()),
            context={"source": "telegram", "command": "agent"},
        )
        
        # Restore original provider
        agent.llm_provider = original_provider
        
        # Format response based on AgentContext result
        if result.error:
            await status_msg.edit_text(
                f"❌ <b>Agent 執行失敗</b>\n\n{result.error}",
                parse_mode="HTML",
            )
        elif result.final_response:
            response = result.final_response[:4000]
            await status_msg.edit_text(
                f"✅ <b>Agent 完成</b>\n\n"
                f"執行了 {result.step_count} 個步驟\n\n"
                f"{response}",
                parse_mode="HTML",
            )
        else:
            await status_msg.edit_text(
                f"✅ <b>Agent 完成</b>\n\n"
                f"執行了 {result.step_count} 個步驟",
                parse_mode="HTML",
            )
            
    except Exception as e:
        logger.error(f"Agent handler error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await status_msg.edit_text(
            f"❌ Agent 執行錯誤: {str(e)[:200]}",
            parse_mode="HTML",
        )


# ============================================
# Model Selection Commands
# ============================================


@authorized_only
async def model_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /model command.
    List available models and switch between them.
    
    Usage:
        /model - Show current model and available options
        /model list - List all available providers and models
        /model set <provider> [model] - Set model for this user
        /model reset - Reset to default model
    """
    from ..core.llm_providers import get_llm_manager
    
    user_id = str(update.effective_user.id)
    args = context.args or []
    manager = get_llm_manager()
    
    if not args or args[0] == "status":
        # Show current status
        status = manager.get_current_status(user_id)
        
        if not status["available_providers"]:
            await update.message.reply_text(
                "❌ <b>沒有可用的 AI 模型</b>\n\n"
                "請在 .env 中設定至少一個提供者的 API Key：\n"
                "• OPENAI_API_KEY\n"
                "• GOOGLE_GENERATIVE_AI_API_KEY\n"
                "• ANTHROPIC_API_KEY\n"
                "• OPENROUTER_API_KEY\n"
                "• OLLAMA_ENABLED=true",
                parse_mode="HTML",
            )
            return
        
        # Build status message
        current = f"{status['current_provider']}/{status['current_model']}" if status["current_provider"] else "未設定"
        selection_type = "（自選）" if status["is_user_selection"] else "（預設）"
        
        text = f"🤖 <b>AI 模型狀態</b>\n\n"
        text += f"<b>目前使用：</b> <code>{current}</code> {selection_type}\n\n"
        text += f"<b>可用提供者：</b>\n"
        
        provider_icons = {
            "openai": "🟢",
            "google": "🔵",
            "anthropic": "🟠",
            "openrouter": "🟣",
            "ollama": "⚪",
            "custom": "⚙️",
        }
        
        for provider in status["available_providers"]:
            icon = provider_icons.get(provider, "•")
            models = status["available_models"].get(provider, [])
            model_preview = ", ".join(models[:3])
            if len(models) > 3:
                model_preview += f" (+{len(models)-3})"
            text += f"{icon} <b>{provider}</b>: {model_preview}\n"
        
        text += "\n<b>指令：</b>\n"
        text += "• <code>/model list</code> - 顯示所有模型\n"
        text += "• <code>/model set &lt;provider&gt; [model]</code> - 切換模型\n"
        text += "• <code>/model reset</code> - 恢復預設\n"
        
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    elif args[0] == "list":
        # List all models
        status = manager.get_current_status(user_id)
        
        if not status["available_providers"]:
            await update.message.reply_text("❌ 沒有可用的 AI 模型")
            return
        
        text = "📋 <b>可用 AI 模型列表</b>\n\n"
        
        provider_names = {
            "openai": "OpenAI",
            "google": "Google Gemini",
            "anthropic": "Anthropic Claude",
            "openrouter": "OpenRouter",
            "ollama": "Ollama (本地)",
            "custom": "自訂端點",
        }
        
        for provider in status["available_providers"]:
            name = provider_names.get(provider, provider)
            models = status["available_models"].get(provider, [])
            
            text += f"<b>{name}</b>\n"
            for model in models:
                text += f"  • <code>{model}</code>\n"
            text += "\n"
        
        text += "<b>切換方式：</b>\n"
        text += "<code>/model set openai gpt-4o</code>\n"
        text += "<code>/model set anthropic claude-3-5-sonnet-20241022</code>\n"
        
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    elif args[0] == "set" and len(args) >= 2:
        # Set model
        provider = args[1].lower()
        model = args[2] if len(args) >= 3 else None
        
        if manager.set_user_model(user_id, provider, model):
            current = manager.get_user_model(user_id)
            if current:
                await update.message.reply_text(
                    f"✅ <b>已切換 AI 模型</b>\n\n"
                    f"提供者：<code>{current[0]}</code>\n"
                    f"模型：<code>{current[1]}</code>",
                    parse_mode="HTML",
                )
            else:
                await update.message.reply_text("✅ 模型已設定")
        else:
            available = manager.list_available_providers()
            await update.message.reply_text(
                f"❌ 無效的提供者：<code>{provider}</code>\n\n"
                f"可用的提供者：{', '.join(available)}",
                parse_mode="HTML",
            )
        return
    
    elif args[0] == "reset":
        # Reset to default
        manager.clear_user_model(user_id)
        status = manager.get_current_status(user_id)
        
        current = f"{status['current_provider']}/{status['current_model']}" if status["current_provider"] else "未設定"
        
        await update.message.reply_text(
            f"🔄 <b>已恢復預設模型</b>\n\n"
            f"目前使用：<code>{current}</code>",
            parse_mode="HTML",
        )
        return
    
    else:
        await update.message.reply_text(
            "❓ <b>模型指令用法</b>\n\n"
            "• <code>/model</code> - 查看目前狀態\n"
            "• <code>/model list</code> - 列出所有模型\n"
            "• <code>/model set &lt;provider&gt; [model]</code> - 切換模型\n"
            "• <code>/model reset</code> - 恢復預設\n\n"
            "<b>範例：</b>\n"
            "<code>/model set openai gpt-4o</code>\n"
            "<code>/model set anthropic</code>\n"
            "<code>/model set ollama llama3.2</code>",
            parse_mode="HTML",
        )


def setup_core_handlers(app) -> None:
    """
    Setup core feature handlers.

    Args:
        app: Telegram Application instance
    """
    # Agent command
    app.add_handler(CommandHandler("agent", agent_handler))
    
    # Model selection command
    app.add_handler(CommandHandler("model", model_handler))
    
    # Memory commands
    app.add_handler(CommandHandler("memory", memory_handler))

    # Skills commands
    app.add_handler(CommandHandler("skills", skills_handler))

    # Scheduler commands
    app.add_handler(CommandHandler("schedule", schedule_handler))

    # Context commands
    app.add_handler(CommandHandler("clear", clear_context_handler))

    # Stats commands
    app.add_handler(CommandHandler("stats", stats_handler))

    # Settings commands
    app.add_handler(CommandHandler("settings", settings_handler))

    # Built-in skill commands
    skill_commands = ["translate", "tr", "summarize", "sum", "calc", "calculate", "remind", "reminder"]
    for cmd in skill_commands:
        app.add_handler(CommandHandler(cmd, skill_command_handler))

    logger.info("Core handlers configured")


__all__ = [
    "agent_handler",
    "model_handler",
    "memory_handler",
    "skills_handler",
    "schedule_handler",
    "clear_context_handler",
    "stats_handler",
    "settings_handler",
    "setup_core_handlers",
]

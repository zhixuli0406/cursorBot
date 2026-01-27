"""
Core feature handlers for Telegram Bot
Integrates memory, skills, approvals, and other core features
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

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

# Provider display names and emojis
_PROVIDER_NAMES = {
    "openai": "OpenAI",
    "google": "Google Gemini",
    "anthropic": "Anthropic Claude",
    "openrouter": "OpenRouter",
    "ollama": "Ollama (本地)",
    "custom": "自訂端點",
}

_PROVIDER_EMOJIS = {
    "openai": "🤖",
    "google": "🔷",
    "anthropic": "🟠",
    "openrouter": "🌐",
    "ollama": "🦙",
    "custom": "⚙️",
}


def _create_model_provider_view(
    models: dict,
    providers: list,
    current_provider: str = None,
    current_model: str = None,
) -> tuple[str, InlineKeyboardMarkup]:
    """Create provider selection view with model counts."""
    text = "📋 <b>選擇 AI 模型提供者</b>\n\n"
    text += "點擊下方按鈕選擇提供者，然後選擇模型。\n\n"
    
    total_models = 0
    for provider in providers:
        name = _PROVIDER_NAMES.get(provider, provider)
        emoji = _PROVIDER_EMOJIS.get(provider, "•")
        model_list = models.get(provider, [])
        count = len(model_list)
        total_models += count
        
        is_current = provider == current_provider
        marker = " ✓" if is_current else ""
        text += f"{emoji} <b>{name}</b>{marker} ({count} 個模型)\n"
    
    text += f"\n<b>共 {total_models} 個模型可用</b>\n"
    
    if current_provider and current_model:
        text += f"\n目前使用: <code>{current_provider}/{current_model}</code>"
    
    # Create provider buttons
    keyboard = []
    row = []
    for i, provider in enumerate(providers):
        emoji = _PROVIDER_EMOJIS.get(provider, "•")
        name = _PROVIDER_NAMES.get(provider, provider)
        is_current = provider == current_provider
        
        # Shorten name for button
        short_name = name.split()[0] if len(name) > 10 else name
        label = f"{emoji} {short_name}" + (" ✓" if is_current else "")
        
        row.append(InlineKeyboardButton(label, callback_data=f"model_provider:{provider}"))
        
        # 2 buttons per row
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Add refresh and close buttons
    keyboard.append([
        InlineKeyboardButton("🔄 重新整理", callback_data="model_refresh"),
        InlineKeyboardButton("❌ 關閉", callback_data="model_close"),
    ])
    
    return text, InlineKeyboardMarkup(keyboard)


def _create_model_list_view(
    provider: str,
    models: list,
    page: int = 0,
    page_size: int = 8,
    current_provider: str = None,
    current_model: str = None,
) -> tuple[str, InlineKeyboardMarkup]:
    """Create paginated model list view for a specific provider."""
    name = _PROVIDER_NAMES.get(provider, provider)
    emoji = _PROVIDER_EMOJIS.get(provider, "•")
    
    total = len(models)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    
    start = page * page_size
    end = min(start + page_size, total)
    page_models = models[start:end]
    
    text = f"{emoji} <b>{name} 模型</b>\n\n"
    text += f"共 {total} 個模型（第 {page + 1}/{total_pages} 頁）\n"
    text += "點擊按鈕切換模型：\n\n"
    
    # Create model buttons
    keyboard = []
    for model in page_models:
        is_current = provider == current_provider and model == current_model
        # Truncate long model names
        display_name = model if len(model) <= 35 else model[:32] + "..."
        label = f"{'✓ ' if is_current else ''}{display_name}"
        
        # Encode model in callback data (URL-safe)
        callback_data = f"model_set:{provider}:{model}"
        
        # Telegram callback_data limit is 64 bytes
        if len(callback_data.encode('utf-8')) > 64:
            # Use index instead
            callback_data = f"model_idx:{provider}:{page}:{page_models.index(model)}"
        
        keyboard.append([InlineKeyboardButton(label, callback_data=callback_data)])
    
    # Navigation buttons
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ 上一頁", callback_data=f"model_page:{provider}:{page - 1}"))
    
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="model_noop"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("下一頁 ▶️", callback_data=f"model_page:{provider}:{page + 1}"))
    
    keyboard.append(nav_row)
    
    # Back and close buttons
    keyboard.append([
        InlineKeyboardButton("⬅️ 返回提供者", callback_data="model_back"),
        InlineKeyboardButton("❌ 關閉", callback_data="model_close"),
    ])
    
    return text, InlineKeyboardMarkup(keyboard)


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
        # List all models with interactive buttons
        status = manager.get_current_status(user_id)
        
        if not status["available_providers"]:
            await update.message.reply_text("❌ 沒有可用的 AI 模型")
            return
        
        # Send loading message
        loading_msg = await update.message.reply_text(
            "🔄 <b>正在從各提供者獲取可用模型...</b>",
            parse_mode="HTML",
        )
        
        # Fetch models from APIs
        try:
            fetched_models = await manager.fetch_all_models(max_per_provider=50)
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            fetched_models = status["available_models"]
        
        # Cache the fetched models in context for pagination
        context.user_data["model_list_cache"] = fetched_models
        context.user_data["model_list_providers"] = status["available_providers"]
        
        # Show provider selection first
        text, keyboard = _create_model_provider_view(
            fetched_models, 
            status["available_providers"],
            status.get("current_provider"),
            status.get("current_model"),
        )
        
        await loading_msg.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
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


@authorized_only
async def model_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle model selection callbacks from inline keyboard.
    """
    from ..core.llm_providers import get_llm_manager
    
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    manager = get_llm_manager()
    
    # Get cached models from context
    cached_models = context.user_data.get("model_list_cache", {})
    providers = context.user_data.get("model_list_providers", [])
    
    # Get current selection
    status = manager.get_current_status(user_id)
    current_provider = status.get("current_provider")
    current_model = status.get("current_model")
    
    if data == "model_close":
        await query.message.delete()
        return
    
    elif data == "model_noop":
        # Do nothing (page indicator button)
        return
    
    elif data == "model_refresh":
        # Refresh model list
        await query.message.edit_text(
            "🔄 <b>正在重新獲取模型列表...</b>",
            parse_mode="HTML",
        )
        
        try:
            fetched_models = await manager.fetch_all_models(max_per_provider=50)
            context.user_data["model_list_cache"] = fetched_models
            providers = manager.list_available_providers()
            context.user_data["model_list_providers"] = providers
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            fetched_models = manager.list_available_models()
            context.user_data["model_list_cache"] = fetched_models
        
        status = manager.get_current_status(user_id)
        text, keyboard = _create_model_provider_view(
            fetched_models,
            providers,
            status.get("current_provider"),
            status.get("current_model"),
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    elif data == "model_back":
        # Go back to provider view
        if not cached_models:
            cached_models = manager.list_available_models()
        if not providers:
            providers = manager.list_available_providers()
        
        text, keyboard = _create_model_provider_view(
            cached_models,
            providers,
            current_provider,
            current_model,
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    elif data.startswith("model_provider:"):
        # Show models for selected provider
        provider = data.split(":", 1)[1]
        
        if not cached_models:
            # Fetch if not cached
            await query.message.edit_text(
                "🔄 <b>正在獲取模型列表...</b>",
                parse_mode="HTML",
            )
            try:
                cached_models = await manager.fetch_all_models(max_per_provider=50)
                context.user_data["model_list_cache"] = cached_models
            except Exception:
                cached_models = manager.list_available_models()
        
        models = cached_models.get(provider, [])
        
        if not models:
            await query.answer("此提供者沒有可用模型", show_alert=True)
            return
        
        text, keyboard = _create_model_list_view(
            provider,
            models,
            page=0,
            current_provider=current_provider,
            current_model=current_model,
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    elif data.startswith("model_page:"):
        # Handle pagination
        parts = data.split(":")
        provider = parts[1]
        page = int(parts[2])
        
        models = cached_models.get(provider, [])
        
        text, keyboard = _create_model_list_view(
            provider,
            models,
            page=page,
            current_provider=current_provider,
            current_model=current_model,
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    elif data.startswith("model_set:"):
        # Set model directly
        parts = data.split(":", 2)
        provider = parts[1]
        model = parts[2] if len(parts) > 2 else None
        
        if manager.set_user_model(user_id, provider, model):
            current = manager.get_user_model(user_id)
            status = manager.get_current_status(user_id)
            
            # Update the view to show new selection
            models = cached_models.get(provider, [])
            page = 0
            
            # Find current page
            if model and model in models:
                idx = models.index(model)
                page = idx // 8
            
            text, keyboard = _create_model_list_view(
                provider,
                models,
                page=page,
                current_provider=status.get("current_provider"),
                current_model=status.get("current_model"),
            )
            
            # Add success message
            success_text = f"✅ 已切換至 <code>{provider}/{model}</code>\n\n" + text
            
            await query.message.edit_text(success_text, parse_mode="HTML", reply_markup=keyboard)
            await query.answer("✅ 模型已切換")
        else:
            await query.answer("❌ 切換失敗", show_alert=True)
        return
    
    elif data.startswith("model_idx:"):
        # Set model by index (for long model names)
        parts = data.split(":")
        provider = parts[1]
        page = int(parts[2])
        idx = int(parts[3])
        
        models = cached_models.get(provider, [])
        page_size = 8
        model_idx = page * page_size + idx
        
        if 0 <= model_idx < len(models):
            model = models[model_idx]
            
            if manager.set_user_model(user_id, provider, model):
                status = manager.get_current_status(user_id)
                
                text, keyboard = _create_model_list_view(
                    provider,
                    models,
                    page=page,
                    current_provider=status.get("current_provider"),
                    current_model=status.get("current_model"),
                )
                
                success_text = f"✅ 已切換至 <code>{provider}/{model}</code>\n\n" + text
                await query.message.edit_text(success_text, parse_mode="HTML", reply_markup=keyboard)
                await query.answer("✅ 模型已切換")
            else:
                await query.answer("❌ 切換失敗", show_alert=True)
        return
    
    else:
        logger.warning(f"Unknown model callback: {data}")


# ============================================
# Doctor - System Diagnostics
# ============================================


@authorized_only
async def doctor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /doctor command.
    Run system diagnostics.
    
    Usage:
        /doctor - Run full diagnostics
        /doctor quick - Quick health check
    """
    args = context.args or []
    
    await update.message.reply_text("🩺 正在執行系統診斷...")
    
    try:
        from ..core.doctor import get_doctor
        doctor = get_doctor()
        
        if args and args[0] == "quick":
            # Quick check
            results = []
            for name in ["python_version", "telegram_config", "llm_providers"]:
                result = await doctor.run_check(name)
                if result:
                    icon = {"ok": "✅", "warning": "⚠️", "error": "❌", "critical": "☠️", "info": "ℹ️"}
                    results.append(f"{icon.get(result.level.value, '•')} {result.name}: {result.message}")
            
            text = "🩺 <b>快速診斷結果</b>\n\n" + "\n".join(results)
        else:
            # Full diagnostics
            report = await doctor.run_all_checks()
            
            # Format report
            lines = [
                f"🩺 <b>系統診斷報告</b>",
                f"📅 {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                f"📊 整體狀態: <b>{report.overall_status.value.upper()}</b>",
                "",
            ]
            
            # Group by level
            for level_name, icon in [("critical", "☠️"), ("error", "❌"), ("warning", "⚠️"), ("ok", "✅")]:
                level_results = [r for r in report.results if r.level.value == level_name]
                if level_results:
                    for r in level_results[:5]:  # Limit to 5 per level
                        lines.append(f"{icon} <b>{r.name}</b>: {r.message}")
                        if r.recommendation:
                            lines.append(f"   → {r.recommendation}")
            
            # Summary
            lines.append("")
            lines.append(f"📈 <b>統計</b>: {report.summary.get('ok', 0)} 通過 / "
                        f"{report.summary.get('warnings', 0)} 警告 / "
                        f"{report.summary.get('errors', 0)} 錯誤")
            
            text = "\n".join(lines)
        
        await update.message.reply_text(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Doctor error: {e}")
        await update.message.reply_text(f"❌ 診斷失敗: {e}")


# ============================================
# Sessions - Session Management
# ============================================


@authorized_only
async def sessions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /sessions command.
    Manage conversation sessions.
    
    Usage:
        /sessions - Show session stats
        /sessions list - List active sessions
        /sessions prune - Clean expired sessions
        /sessions clear - Clear all sessions
    """
    args = context.args or []
    ctx_manager = get_context_manager()
    
    if not args or args[0] == "stats":
        # Show stats
        stats = ctx_manager.get_session_stats()
        
        text = f"""📊 <b>會話統計</b>

• 總會話數: <b>{stats['total_sessions']}</b>
• 總訊息數: <b>{stats['total_messages']}</b>
• 平均訊息/會話: <b>{stats['avg_messages_per_session']:.1f}</b>

<b>按類型:</b>
"""
        for ct, count in stats.get("by_chat_type", {}).items():
            text += f"  • {ct}: {count}\n"
        
        text += "\n<b>按狀態:</b>\n"
        for status, count in stats.get("by_status", {}).items():
            text += f"  • {status}: {count}\n"
        
        if stats.get("oldest_session"):
            text += f"\n🕐 最舊會話: {stats['oldest_session']['age_minutes']:.0f} 分鐘前"
        
        await update.message.reply_text(text, parse_mode="HTML")
        
    elif args[0] == "list":
        # List sessions
        contexts = list(ctx_manager._contexts.items())[:10]
        
        if not contexts:
            await update.message.reply_text("📭 目前沒有活躍會話")
            return
        
        lines = ["📋 <b>活躍會話</b> (前 10 個)\n"]
        for key, ctx in contexts:
            status = "🔴 過期" if ctx.is_expired else "🟢 活躍"
            lines.append(f"• <code>{key}</code> {status}")
            lines.append(f"  訊息: {len(ctx.messages)} | 類型: {ctx.chat_type}")
        
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
    elif args[0] == "prune":
        # Prune expired sessions
        result = ctx_manager.prune_expired_sessions()
        
        await update.message.reply_text(
            f"🧹 <b>會話清理完成</b>\n\n"
            f"• 已清理: <b>{result['pruned_count']}</b> 個會話\n"
            f"• 剩餘: <b>{result['remaining_count']}</b> 個會話",
            parse_mode="HTML"
        )
        
    elif args[0] == "clear":
        # Clear all sessions (admin only)
        ctx_manager._contexts.clear()
        await update.message.reply_text("🗑️ 已清除所有會話")
        
    else:
        await update.message.reply_text(
            "📖 <b>會話管理</b>\n\n"
            "<code>/sessions</code> - 顯示統計\n"
            "<code>/sessions list</code> - 列出會話\n"
            "<code>/sessions prune</code> - 清理過期\n"
            "<code>/sessions clear</code> - 清除全部",
            parse_mode="HTML"
        )


# ============================================
# Patch - Git Patch Management
# ============================================


@authorized_only
async def patch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /patch command.
    Manage Git patches.
    
    Usage:
        /patch - Show patch help
        /patch create - Create patch from changes
        /patch list - List patch history
        /patch apply <content> - Apply a patch
    """
    args = context.args or []
    
    try:
        from ..core.patch import get_patch_manager
        pm = get_patch_manager()
        
        if not args:
            await update.message.reply_text(
                "📝 <b>補丁管理</b>\n\n"
                "<code>/patch create</code> - 從當前變更建立補丁\n"
                "<code>/patch create --staged</code> - 從暫存區建立\n"
                "<code>/patch list</code> - 顯示補丁歷史\n"
                "<code>/patch stats</code> - 顯示統計\n"
                "<code>/patch check</code> - 檢查補丁（回覆補丁內容）",
                parse_mode="HTML"
            )
            return
        
        if args[0] == "create":
            staged = "--staged" in args
            patch_content = await pm.create_patch(staged=staged)
            
            if patch_content:
                # Truncate if too long
                if len(patch_content) > 3500:
                    patch_content = patch_content[:3500] + "\n... (已截斷)"
                
                await update.message.reply_text(
                    f"📝 <b>已建立補丁</b>\n\n<pre>{patch_content}</pre>",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("📭 沒有變更可建立補丁")
        
        elif args[0] == "list":
            history = pm.get_history(limit=10)
            
            if not history:
                await update.message.reply_text("📭 沒有補丁歷史")
                return
            
            lines = ["📋 <b>補丁歷史</b>\n"]
            for p in history:
                status_icon = {"applied": "✅", "failed": "❌", "reverted": "↩️", "pending": "⏳"}
                lines.append(f"• <code>{p['id']}</code> {status_icon.get(p['status'], '•')} {p['status']}")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "stats":
            stats = pm.get_stats()
            await update.message.reply_text(
                f"📊 <b>補丁統計</b>\n\n"
                f"• 總數: {stats['total_patches']}\n"
                f"• 已套用: {stats['applied']}\n"
                f"• 失敗: {stats['failed']}\n"
                f"• 已還原: {stats['reverted']}",
                parse_mode="HTML"
            )
        
        elif args[0] == "check":
            # Check if replying to a message with patch content
            if update.message.reply_to_message:
                patch_content = update.message.reply_to_message.text
                result = await pm.check_patch(patch_content)
                
                if result.success:
                    await update.message.reply_text(
                        f"✅ 補丁可套用\n\n"
                        f"影響檔案: {len(result.affected_files)}\n"
                        f"新增: +{result.diff_stats.get('additions', 0)}\n"
                        f"刪除: -{result.diff_stats.get('deletions', 0)}"
                    )
                else:
                    await update.message.reply_text(f"❌ 補丁無法套用: {result.error}")
            else:
                await update.message.reply_text("請回覆包含補丁內容的訊息")
        
        else:
            await update.message.reply_text("❓ 未知的子命令，使用 /patch 查看說明")
            
    except Exception as e:
        logger.error(f"Patch error: {e}")
        await update.message.reply_text(f"❌ 補丁操作失敗: {e}")


# ============================================
# Policy - Tool Policy Management
# ============================================


@authorized_only
async def policy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /policy command.
    Manage tool access policies.
    
    Usage:
        /policy - Show policy status
        /policy list - List all policies
        /policy audit - Show audit log
        /policy set <tool> <on|off> - Enable/disable tool
    """
    args = context.args or []
    
    try:
        from ..core.tool_policy import get_tool_policy_manager
        pm = get_tool_policy_manager()
        
        if not args or args[0] == "status":
            stats = pm.get_stats()
            
            await update.message.reply_text(
                f"🔒 <b>工具策略狀態</b>\n\n"
                f"• 全域啟用: {'✅ 是' if stats['global_enabled'] else '❌ 否'}\n"
                f"• 策略總數: {stats['total_policies']}\n"
                f"• 已啟用: {stats['enabled_policies']}\n"
                f"• 管理員數: {stats['admin_users']}\n"
                f"• 審計記錄: {stats['audit_log_entries']}",
                parse_mode="HTML"
            )
        
        elif args[0] == "list":
            policies = pm.get_all_policies()
            
            if not policies:
                await update.message.reply_text("📭 沒有設定任何策略")
                return
            
            lines = ["📋 <b>工具策略清單</b>\n"]
            for p in policies:
                status = "✅" if p['enabled'] else "❌"
                lines.append(f"• {status} <code>{p['tool_name']}</code> [{p['permission_level']}]")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "audit":
            entries = pm.get_audit_log(limit=10)
            
            if not entries:
                await update.message.reply_text("📭 沒有審計記錄")
                return
            
            lines = ["📋 <b>審計日誌</b> (最近 10 筆)\n"]
            for e in entries:
                icon = "✅" if e['allowed'] else "❌"
                lines.append(f"• {icon} {e['tool_name']} - {e['action']} (用戶 {e['user_id']})")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "set" and len(args) >= 3:
            tool_name = args[1]
            action = args[2].lower()
            
            from ..core.tool_policy import ToolPolicy
            
            if action in ("on", "enable", "1"):
                policy = pm.get_policy(tool_name) or ToolPolicy(tool_name=tool_name)
                policy.enabled = True
                pm.set_policy(policy)
                await update.message.reply_text(f"✅ 已啟用工具: {tool_name}")
            elif action in ("off", "disable", "0"):
                policy = pm.get_policy(tool_name) or ToolPolicy(tool_name=tool_name)
                policy.enabled = False
                pm.set_policy(policy)
                await update.message.reply_text(f"❌ 已停用工具: {tool_name}")
            else:
                await update.message.reply_text("❓ 請使用 on 或 off")
        
        else:
            await update.message.reply_text(
                "🔒 <b>工具策略管理</b>\n\n"
                "<code>/policy</code> - 顯示狀態\n"
                "<code>/policy list</code> - 列出策略\n"
                "<code>/policy audit</code> - 審計日誌\n"
                "<code>/policy set &lt;tool&gt; on|off</code> - 啟用/停用",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Policy error: {e}")
        await update.message.reply_text(f"❌ 策略操作失敗: {e}")


# ============================================
# TTS - Text to Speech
# ============================================


@authorized_only
async def tts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tts command.
    Convert text to speech.
    
    Usage:
        /tts <text> - Convert text to speech
        /tts providers - List available providers
    """
    args = context.args or []
    
    if not args:
        await update.message.reply_text(
            "🔊 <b>語音合成</b>\n\n"
            "<code>/tts &lt;文字&gt;</code> - 將文字轉為語音\n"
            "<code>/tts providers</code> - 查看可用服務\n\n"
            "或直接回覆訊息使用 /tts",
            parse_mode="HTML"
        )
        return
    
    if args[0] == "providers":
        from ..core.tts import TTSProvider
        providers = [p.value for p in TTSProvider]
        await update.message.reply_text(
            f"🔊 <b>可用 TTS 服務</b>\n\n" +
            "\n".join(f"• {p}" for p in providers),
            parse_mode="HTML"
        )
        return
    
    # Get text to convert
    text = " ".join(args)
    if not text and update.message.reply_to_message:
        text = update.message.reply_to_message.text
    
    if not text:
        await update.message.reply_text("請提供要轉換的文字")
        return
    
    try:
        from ..core.tts import text_to_speech
        
        await update.message.reply_text("🔊 正在合成語音...")
        
        result = await text_to_speech(text)
        
        if result.success and result.audio_data:
            from io import BytesIO
            audio_file = BytesIO(result.audio_data)
            audio_file.name = "speech.mp3"
            
            await update.message.reply_voice(
                voice=audio_file,
                caption=f"🔊 TTS ({result.provider})"
            )
        else:
            await update.message.reply_text(f"❌ 語音合成失敗: {result.error}")
            
    except Exception as e:
        logger.error(f"TTS error: {e}")
        await update.message.reply_text(f"❌ TTS 錯誤: {e}")


# ============================================
# Broadcast - Send message to all users
# ============================================


@authorized_only
async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /broadcast command.
    Send message to all allowed users.
    
    Usage:
        /broadcast <message> - Send message to all users
    """
    args = context.args or []
    
    if not args:
        await update.message.reply_text(
            "📢 <b>廣播訊息</b>\n\n"
            "<code>/broadcast &lt;訊息&gt;</code> - 發送訊息給所有用戶",
            parse_mode="HTML"
        )
        return
    
    message = " ".join(args)
    
    try:
        from ..utils.config import settings
        
        allowed_users = settings.telegram_allowed_users
        if not allowed_users:
            await update.message.reply_text("❌ 沒有設定允許的用戶")
            return
        
        await update.message.reply_text(f"📢 正在廣播訊息給 {len(allowed_users)} 位用戶...")
        
        success_count = 0
        failed_count = 0
        
        for user_id in allowed_users:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 <b>系統廣播</b>\n\n{message}",
                    parse_mode="HTML"
                )
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to send broadcast to {user_id}: {e}")
                failed_count += 1
        
        await update.message.reply_text(
            f"📢 <b>廣播完成</b>\n\n"
            f"✅ 成功: {success_count}\n"
            f"❌ 失敗: {failed_count}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text(f"❌ 廣播失敗: {e}")


# ============================================
# Usage - Show usage statistics
# ============================================


@authorized_only
async def usage_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /usage command.
    Show usage statistics.
    
    Usage:
        /usage - Show usage stats
        /usage me - Show my usage
    """
    args = context.args or []
    user_id = update.effective_user.id
    
    try:
        from ..core.llm_providers import get_llm_manager
        manager = get_llm_manager()
        stats = manager.get_usage_stats()
        
        if args and args[0] == "me":
            # Show user's usage
            user_calls = stats.get("by_user", {}).get(user_id, 0)
            await update.message.reply_text(
                f"📊 <b>我的使用統計</b>\n\n"
                f"API 呼叫次數: <b>{user_calls}</b>",
                parse_mode="HTML"
            )
        else:
            # Show overall stats
            text = f"""📊 <b>使用統計</b>

總 API 呼叫: <b>{stats.get('total_calls', 0)}</b>

<b>按提供者:</b>
"""
            for provider, count in stats.get('by_provider', {}).items():
                text += f"  • {provider}: {count}\n"
            
            text += "\n<b>前 5 名用戶:</b>\n"
            sorted_users = sorted(
                stats.get('by_user', {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            for uid, count in sorted_users:
                text += f"  • 用戶 {uid}: {count}\n"
            
            await update.message.reply_text(text, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Usage error: {e}")
        await update.message.reply_text(f"❌ 無法取得使用統計: {e}")


# ============================================
# Permissions - Manage permissions
# ============================================


@authorized_only
async def permissions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /permissions command.
    Manage user and group permissions.
    
    Usage:
        /permissions - Show permission status
        /permissions user <id> - Show user permissions
        /permissions group - Show group settings
        /permissions admin add <id> - Add group admin
        /permissions whitelist add <id> - Add to whitelist
    """
    args = context.args or []
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    try:
        from ..core.permissions import get_permission_manager, Role
        pm = get_permission_manager()
        
        if not args:
            # Show overall stats
            stats = pm.get_stats()
            await update.message.reply_text(
                f"🔐 <b>權限系統狀態</b>\n\n"
                f"• 全域管理員: {stats['global_admins']}\n"
                f"• 全域黑名單: {stats['global_blacklist']}\n"
                f"• 已設定用戶: {stats['users_with_permissions']}\n"
                f"• 已設定群組: {stats['groups_configured']}\n"
                f"• 提升中用戶: {stats['elevated_users']}",
                parse_mode="HTML"
            )
            return
        
        if args[0] == "user" and len(args) >= 2:
            # Show user permissions
            target_id = int(args[1])
            perms = pm.get_user_permissions(target_id)
            
            await update.message.reply_text(
                f"👤 <b>用戶權限</b> ({target_id})\n\n"
                f"• 角色: {perms.role.value}\n"
                f"• 全域管理員: {'是' if pm.is_global_admin(target_id) else '否'}\n"
                f"• 提升中: {'是' if pm.is_elevated(target_id) else '否'}\n"
                f"• 自訂權限: {len(perms.custom_permissions)}\n"
                f"• 拒絕權限: {len(perms.denied_permissions)}",
                parse_mode="HTML"
            )
            return
        
        if args[0] == "group":
            # Show group settings
            if chat_type == "private":
                await update.message.reply_text("此指令僅限群組使用")
                return
            
            group = pm.get_group_settings(chat_id)
            await update.message.reply_text(
                f"👥 <b>群組設定</b>\n\n"
                f"• 已啟用: {'是' if group.enabled else '否'}\n"
                f"• 白名單模式: {'是' if group.whitelist_mode else '否'}\n"
                f"• 管理員數: {len(group.admins)}\n"
                f"• 版主數: {len(group.moderators)}\n"
                f"• 白名單: {len(group.whitelist)}\n"
                f"• 黑名單: {len(group.blacklist)}\n"
                f"• 停用指令: {len(group.disabled_commands)}",
                parse_mode="HTML"
            )
            return
        
        if args[0] == "admin" and len(args) >= 3:
            action = args[1]
            target_id = int(args[2])
            
            if chat_type == "private":
                await update.message.reply_text("此指令僅限群組使用")
                return
            
            if action == "add":
                pm.add_group_admin(chat_id, target_id)
                await update.message.reply_text(f"✅ 已將用戶 {target_id} 設為群組管理員")
            elif action == "remove":
                pm.remove_group_admin(chat_id, target_id)
                await update.message.reply_text(f"✅ 已移除用戶 {target_id} 的管理員權限")
            return
        
        if args[0] == "whitelist" and len(args) >= 3:
            action = args[1]
            target_id = int(args[2])
            
            if chat_type == "private":
                await update.message.reply_text("此指令僅限群組使用")
                return
            
            if action == "add":
                pm.add_to_whitelist(chat_id, target_id)
                await update.message.reply_text(f"✅ 已將用戶 {target_id} 加入白名單")
            elif action == "remove":
                group = pm.get_group_settings(chat_id)
                group.whitelist.discard(target_id)
                await update.message.reply_text(f"✅ 已將用戶 {target_id} 從白名單移除")
            return
        
        if args[0] == "blacklist" and len(args) >= 3:
            action = args[1]
            target_id = int(args[2])
            
            if action == "add":
                if chat_type == "private":
                    pm.add_to_global_blacklist(target_id)
                    await update.message.reply_text(f"✅ 已將用戶 {target_id} 加入全域黑名單")
                else:
                    pm.add_to_blacklist(chat_id, target_id)
                    await update.message.reply_text(f"✅ 已將用戶 {target_id} 加入群組黑名單")
            elif action == "remove":
                if chat_type == "private":
                    pm.remove_from_global_blacklist(target_id)
                    await update.message.reply_text(f"✅ 已將用戶 {target_id} 從全域黑名單移除")
            return
        
        # Show help
        await update.message.reply_text(
            "🔐 <b>權限管理</b>\n\n"
            "<code>/permissions</code> - 顯示狀態\n"
            "<code>/permissions user &lt;id&gt;</code> - 查看用戶\n"
            "<code>/permissions group</code> - 群組設定\n"
            "<code>/permissions admin add|remove &lt;id&gt;</code>\n"
            "<code>/permissions whitelist add|remove &lt;id&gt;</code>\n"
            "<code>/permissions blacklist add|remove &lt;id&gt;</code>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Permissions error: {e}")
        await update.message.reply_text(f"❌ 權限操作失敗: {e}")


# ============================================
# Elevate - Temporary elevated permissions
# ============================================


@authorized_only
async def elevate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /elevate command.
    Grant or check elevated permissions.
    
    Usage:
        /elevate - Check elevation status
        /elevate <minutes> - Request elevation
        /elevate revoke - Revoke elevation
    """
    args = context.args or []
    user_id = update.effective_user.id
    
    try:
        from ..core.permissions import get_permission_manager
        pm = get_permission_manager()
        
        if not args:
            # Check status
            is_elevated = pm.is_elevated(user_id)
            perms = pm.get_user_permissions(user_id)
            
            if is_elevated:
                remaining = (perms.elevated_until - datetime.now()).total_seconds() / 60
                await update.message.reply_text(
                    f"⬆️ <b>提升狀態</b>\n\n"
                    f"狀態: 🟢 已提升\n"
                    f"剩餘時間: {remaining:.0f} 分鐘",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text(
                    f"⬆️ <b>提升狀態</b>\n\n"
                    f"狀態: ⚪ 未提升\n\n"
                    f"使用 <code>/elevate &lt;分鐘&gt;</code> 請求提升",
                    parse_mode="HTML"
                )
            return
        
        if args[0] == "revoke":
            pm.revoke_elevation(user_id)
            await update.message.reply_text("✅ 已撤銷提升權限")
            return
        
        # Request elevation
        try:
            minutes = int(args[0])
            if minutes < 1 or minutes > 120:
                await update.message.reply_text("⚠️ 提升時間需在 1-120 分鐘之間")
                return
            
            # Check if user is allowed to self-elevate
            if not pm.is_global_admin(user_id):
                await update.message.reply_text("❌ 只有全域管理員可以自行提升權限")
                return
            
            pm.elevate_user(user_id, minutes)
            await update.message.reply_text(
                f"⬆️ <b>權限已提升</b>\n\n"
                f"持續時間: {minutes} 分鐘\n"
                f"您現在擁有提升權限",
                parse_mode="HTML"
            )
            
        except ValueError:
            await update.message.reply_text("❌ 請輸入有效的分鐘數")
            
    except Exception as e:
        logger.error(f"Elevate error: {e}")
        await update.message.reply_text(f"❌ 提升操作失敗: {e}")


# Need to import datetime for elevate handler
from datetime import datetime


# ============================================
# Lock - Gateway Lock Management
# ============================================


@authorized_only
async def lock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /lock command.
    Control gateway locking.
    
    Usage:
        /lock - Show lock status
        /lock on [message] - Lock the bot
        /lock off - Unlock the bot
        /lock maintenance [minutes] - Enter maintenance mode
        /lock user <id> - Lock a user
        /lock group - Lock current group
    """
    args = context.args or []
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        from ..core.gateway_lock import get_gateway_lock, LockReason
        gl = get_gateway_lock()
        
        if not args:
            # Show status
            info = gl.get_lock_info()
            stats = gl.get_stats()
            
            status = "🔒 已鎖定" if info.is_active() else "🔓 未鎖定"
            
            text = f"""🔐 <b>閘道鎖定狀態</b>

狀態: {status}
"""
            if info.is_active():
                text += f"原因: {info.reason.value}\n"
                text += f"訊息: {info.message or '(無)'}\n"
                remaining = info.time_remaining()
                if remaining:
                    text += f"剩餘: {remaining.seconds // 60} 分鐘\n"
            
            text += f"""
<b>統計:</b>
• 鎖定用戶: {stats['locked_users']}
• 鎖定群組: {stats['locked_groups']}
• IP 黑名單: {stats['blacklisted_ips']}
"""
            await update.message.reply_text(text, parse_mode="HTML")
            return
        
        action = args[0].lower()
        
        if action in ("on", "lock"):
            message = " ".join(args[1:]) if len(args) > 1 else "Bot is locked"
            gl.lock(LockReason.MANUAL, message, locked_by=user_id)
            await update.message.reply_text("🔒 閘道已鎖定")
        
        elif action in ("off", "unlock"):
            if gl.unlock(user_id):
                await update.message.reply_text("🔓 閘道已解鎖")
            else:
                await update.message.reply_text("閘道未處於鎖定狀態")
        
        elif action == "maintenance":
            minutes = int(args[1]) if len(args) > 1 else 30
            gl.maintenance_mode(minutes, locked_by=user_id)
            await update.message.reply_text(f"🔧 已進入維護模式 ({minutes} 分鐘)")
        
        elif action == "emergency":
            gl.emergency_lockdown(user_id)
            await update.message.reply_text("🚨 緊急鎖定已啟動")
        
        elif action == "user" and len(args) >= 2:
            target_id = int(args[1])
            minutes = int(args[2]) if len(args) > 2 else None
            gl.lock_user(target_id, duration_minutes=minutes)
            await update.message.reply_text(f"🔒 已鎖定用戶 {target_id}")
        
        elif action == "group":
            minutes = int(args[1]) if len(args) > 1 else None
            gl.lock_group(chat_id, duration_minutes=minutes)
            await update.message.reply_text("🔒 已鎖定此群組")
        
        elif action == "history":
            history = gl.get_history(10)
            if not history:
                await update.message.reply_text("📜 沒有鎖定歷史")
                return
            
            lines = ["📜 <b>鎖定歷史</b>\n"]
            for h in history:
                lines.append(f"• {h['action']} {h['target']} ({h['reason'] or '-'})")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        else:
            await update.message.reply_text(
                "🔐 <b>閘道鎖定</b>\n\n"
                "<code>/lock</code> - 顯示狀態\n"
                "<code>/lock on [訊息]</code> - 鎖定\n"
                "<code>/lock off</code> - 解鎖\n"
                "<code>/lock maintenance [分鐘]</code> - 維護模式\n"
                "<code>/lock emergency</code> - 緊急鎖定\n"
                "<code>/lock user &lt;id&gt; [分鐘]</code> - 鎖定用戶\n"
                "<code>/lock group [分鐘]</code> - 鎖定群組\n"
                "<code>/lock history</code> - 查看歷史",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Lock error: {e}")
        await update.message.reply_text(f"❌ 鎖定操作失敗: {e}")


# ============================================
# Location - Location Sharing
# ============================================


@authorized_only
async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /location command.
    Manage location sharing.
    
    Usage:
        /location - Show location help
        /location share - Share current location
        /location get <id> - Get shared location
        /location stop - Stop sharing
    """
    args = context.args or []
    user_id = update.effective_user.id
    
    try:
        from ..core.location import get_location_manager
        lm = get_location_manager()
        
        if not args:
            stats = lm.get_stats()
            await update.message.reply_text(
                f"📍 <b>位置服務</b>\n\n"
                f"• 用戶位置: {stats['users_with_location']}\n"
                f"• 活躍分享: {stats['active_shares']}\n"
                f"• 即時分享: {stats['live_shares']}\n\n"
                f"<b>指令:</b>\n"
                f"<code>/location share</code> - 分享位置\n"
                f"<code>/location get &lt;id&gt;</code> - 取得分享\n"
                f"<code>/location stop</code> - 停止分享\n"
                f"<code>/location my</code> - 我的位置\n\n"
                f"<i>提示: 直接發送位置訊息即可分享</i>",
                parse_mode="HTML"
            )
            return
        
        action = args[0].lower()
        
        if action == "share":
            # User needs to send a location message
            await update.message.reply_text(
                "📍 請發送位置訊息來分享您的位置\n\n"
                "點擊附件圖示 📎 -> 位置 -> 發送位置"
            )
        
        elif action == "get" and len(args) >= 2:
            share_id = args[1]
            share = lm.get_shared_location(share_id)
            
            if not share:
                await update.message.reply_text("❌ 找不到此位置分享或已過期")
                return
            
            loc = share.location
            await update.message.reply_location(
                latitude=loc.latitude,
                longitude=loc.longitude,
            )
            
            await update.message.reply_text(
                f"📍 <b>位置資訊</b>\n\n"
                f"座標: {loc.latitude:.6f}, {loc.longitude:.6f}\n"
                f"地址: {loc.address or '(未知)'}\n"
                f"🔗 {loc.to_google_maps_url()}",
                parse_mode="HTML"
            )
        
        elif action == "stop":
            lm.stop_live_sharing(user_id)
            lm.clear_user_location(user_id)
            await update.message.reply_text("✅ 已停止位置分享")
        
        elif action == "my":
            loc = lm.get_user_location(user_id)
            if not loc:
                await update.message.reply_text("❌ 沒有您的位置記錄")
                return
            
            await update.message.reply_text(
                f"📍 <b>我的位置</b>\n\n"
                f"座標: {loc.latitude:.6f}, {loc.longitude:.6f}\n"
                f"更新: {loc.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                f"🔗 {loc.to_google_maps_url()}",
                parse_mode="HTML"
            )
        
        else:
            await update.message.reply_text("❓ 未知的子指令")
            
    except Exception as e:
        logger.error(f"Location error: {e}")
        await update.message.reply_text(f"❌ 位置操作失敗: {e}")


# ============================================
# Route - Channel Routing
# ============================================


@authorized_only
async def route_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /route command.
    Manage channel routing.
    
    Usage:
        /route - Show routing stats
        /route list - List channels
        /route add <channel_id> <agent> - Add route
        /route remove <channel_id> - Remove route
    """
    args = context.args or []
    
    try:
        from ..core.channel_routing import get_channel_router
        router = get_channel_router()
        
        if not args:
            stats = router.get_stats()
            await update.message.reply_text(
                f"🔀 <b>頻道路由</b>\n\n"
                f"• 總頻道數: {stats['total_channels']}\n"
                f"• 活躍規則: {stats['active_rules']}\n"
                f"• 處理器: {stats['registered_handlers']}\n"
                f"• 轉發: {'啟用' if stats['forwarding_enabled'] else '停用'}\n"
                f"• 已路由訊息: {stats['total_messages_routed']}",
                parse_mode="HTML"
            )
            return
        
        action = args[0].lower()
        
        if action == "list":
            channels = router.list_channels()
            if not channels:
                await update.message.reply_text("📭 沒有已註冊的頻道")
                return
            
            lines = ["📋 <b>已註冊頻道</b>\n"]
            for ch in channels[:10]:
                status = "✅" if ch.enabled else "❌"
                lines.append(f"• {status} <code>{ch.channel_id}</code>")
                lines.append(f"  類型: {ch.channel_type.value}")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif action == "enable":
            router.enable_forwarding()
            await update.message.reply_text("✅ 已啟用訊息轉發")
        
        elif action == "disable":
            router.disable_forwarding()
            await update.message.reply_text("❌ 已停用訊息轉發")
        
        else:
            await update.message.reply_text(
                "🔀 <b>頻道路由</b>\n\n"
                "<code>/route</code> - 顯示統計\n"
                "<code>/route list</code> - 列出頻道\n"
                "<code>/route enable</code> - 啟用轉發\n"
                "<code>/route disable</code> - 停用轉發",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Route error: {e}")
        await update.message.reply_text(f"❌ 路由操作失敗: {e}")


# ============================================
# Presence - Online Status
# ============================================


@authorized_only
async def presence_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /presence command.
    Manage user online status.
    
    Usage:
        /presence - Show status
        /presence online - Set online
        /presence away - Set away
        /presence busy [text] - Set busy
        /presence offline - Set offline
    """
    args = context.args or []
    user_id = update.effective_user.id
    
    try:
        from ..core.presence import get_presence_manager, PresenceStatus
        pm = get_presence_manager()
        
        if not args:
            presence = pm.get_presence(user_id)
            stats = pm.get_stats()
            
            status = presence.status.value if presence else "offline"
            status_emoji = {
                "online": "🟢",
                "away": "🟡",
                "busy": "🔴",
                "offline": "⚫",
                "invisible": "👻",
            }.get(status, "⚪")
            
            text = f"""👤 <b>在線狀態</b>

您的狀態: {status_emoji} {status}
"""
            if presence and presence.status_text:
                text += f"狀態訊息: {presence.status_text}\n"
            
            text += f"""
<b>全域統計:</b>
• 在線用戶: {stats['online']}
• 5分鐘內活躍: {stats['active_5min']}
• 總追蹤: {stats['total_tracked']}
"""
            await update.message.reply_text(text, parse_mode="HTML")
            return
        
        action = args[0].lower()
        
        if action == "online":
            pm.set_online(user_id, "telegram")
            await update.message.reply_text("🟢 已設為在線")
        
        elif action == "away":
            pm.set_away(user_id)
            await update.message.reply_text("🟡 已設為離開")
        
        elif action == "busy":
            status_text = " ".join(args[1:]) if len(args) > 1 else ""
            pm.set_busy(user_id, status_text)
            await update.message.reply_text("🔴 已設為忙碌")
        
        elif action == "offline":
            pm.set_offline(user_id)
            await update.message.reply_text("⚫ 已設為離線")
        
        elif action == "invisible":
            pm.set_invisible(user_id)
            await update.message.reply_text("👻 已設為隱身")
        
        else:
            await update.message.reply_text(
                "👤 <b>在線狀態</b>\n\n"
                "<code>/presence</code> - 顯示狀態\n"
                "<code>/presence online</code> - 設為在線\n"
                "<code>/presence away</code> - 設為離開\n"
                "<code>/presence busy [訊息]</code> - 設為忙碌\n"
                "<code>/presence offline</code> - 設為離線\n"
                "<code>/presence invisible</code> - 設為隱身",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Presence error: {e}")
        await update.message.reply_text(f"❌ 狀態操作失敗: {e}")


# ============================================
# Gateway - Unified Gateway Info
# ============================================


@authorized_only
async def gateway_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /gateway command.
    Show unified gateway information.
    
    Usage:
        /gateway - Show gateway status
    """
    try:
        from ..core.gateway import get_gateway
        gw = get_gateway()
        stats = gw.get_stats()
        
        adapters = ", ".join(stats.get("adapters", [])) or "(無)"
        
        text = f"""🌐 <b>統一閘道</b>

狀態: {'🟢 運行中' if stats.get('running') else '⚫ 停止'}
已註冊適配器: {adapters}

<b>統計:</b>
• 已接收訊息: {stats.get('messages_received', 0)}
• 已發送訊息: {stats.get('messages_sent', 0)}
• 錯誤: {stats.get('errors', 0)}
• 處理器: {stats.get('handlers', 0)}
• 中介軟體: {stats.get('middleware', 0)}
"""
        await update.message.reply_text(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Gateway error: {e}")
        await update.message.reply_text(f"❌ 閘道查詢失敗: {e}")


# ============================================
# Agents - Agent Management
# ============================================


@authorized_only
async def agents_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /agents command.
    Manage registered agents.
    
    Usage:
        /agents - List agents
        /agents stats - Show statistics
    """
    args = context.args or []
    
    try:
        from ..core.agent_send import get_agent_send_manager
        asm = get_agent_send_manager()
        
        if not args or args[0] == "list":
            agents = asm.list_agents()
            
            if not agents:
                await update.message.reply_text("🤖 沒有已註冊的代理")
                return
            
            lines = ["🤖 <b>已註冊代理</b>\n"]
            for agent in agents:
                status = "🟢" if agent.online else "⚫"
                lines.append(f"• {status} <b>{agent.name}</b> (<code>{agent.agent_id}</code>)")
                if agent.capabilities:
                    lines.append(f"  能力: {', '.join(agent.capabilities[:3])}")
            
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        
        elif args[0] == "stats":
            stats = asm.get_stats()
            
            text = f"""🤖 <b>代理統計</b>

• 已註冊: {stats['registered_agents']}
• 在線: {stats['online_agents']}
• 已發送訊息: {stats['messages_sent']}
• 已送達: {stats['messages_delivered']}
• 失敗: {stats['messages_failed']}
• 待處理回應: {stats['pending_responses']}
"""
            await update.message.reply_text(text, parse_mode="HTML")
        
        else:
            await update.message.reply_text(
                "🤖 <b>代理管理</b>\n\n"
                "<code>/agents</code> - 列出代理\n"
                "<code>/agents stats</code> - 顯示統計",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Agents error: {e}")
        await update.message.reply_text(f"❌ 代理查詢失敗: {e}")


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
    
    # Model selection callback handler
    app.add_handler(CallbackQueryHandler(
        model_callback_handler,
        pattern=r"^model_"
    ))
    
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
    
    # v0.3 New feature commands
    app.add_handler(CommandHandler("doctor", doctor_handler))
    app.add_handler(CommandHandler("sessions", sessions_handler))
    app.add_handler(CommandHandler("patch", patch_handler))
    app.add_handler(CommandHandler("policy", policy_handler))
    app.add_handler(CommandHandler("tts", tts_handler))
    
    # v0.3 Additional commands
    app.add_handler(CommandHandler("broadcast", broadcast_handler))
    app.add_handler(CommandHandler("usage", usage_handler))
    app.add_handler(CommandHandler("permissions", permissions_handler))
    app.add_handler(CommandHandler("perm", permissions_handler))  # Alias
    app.add_handler(CommandHandler("elevate", elevate_handler))
    
    # v0.3 Extended commands
    app.add_handler(CommandHandler("lock", lock_handler))
    app.add_handler(CommandHandler("location", location_handler))
    app.add_handler(CommandHandler("loc", location_handler))  # Alias
    app.add_handler(CommandHandler("route", route_handler))
    
    # v0.3 New commands
    app.add_handler(CommandHandler("presence", presence_handler))
    app.add_handler(CommandHandler("status", presence_handler))  # Alias
    app.add_handler(CommandHandler("gateway", gateway_handler))
    app.add_handler(CommandHandler("agents", agents_handler))

    logger.info("Core handlers configured")


__all__ = [
    "agent_handler",
    "model_handler",
    "model_callback_handler",
    "memory_handler",
    "skills_handler",
    "schedule_handler",
    "clear_context_handler",
    "stats_handler",
    "settings_handler",
    "doctor_handler",
    "sessions_handler",
    "patch_handler",
    "policy_handler",
    "tts_handler",
    "broadcast_handler",
    "usage_handler",
    "permissions_handler",
    "elevate_handler",
    "lock_handler",
    "location_handler",
    "route_handler",
    "presence_handler",
    "gateway_handler",
    "agents_handler",
    "setup_core_handlers",
]

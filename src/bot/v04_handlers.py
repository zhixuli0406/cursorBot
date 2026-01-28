"""
v0.4 Feature Handlers for CursorBot

Telegram command handlers for v0.4 features:
- MCP (Model Context Protocol)
- Workflow Engine
- Analytics
- Code Review
- Conversation Export
- Auto-Documentation
"""

import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..utils.logger import logger
from ..utils.auth import is_authorized


# ============================================
# MCP Handlers
# ============================================

async def mcp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /mcp command - MCP (Model Context Protocol) management.
    
    Usage:
        /mcp - Show MCP status
        /mcp servers - List connected servers
        /mcp connect <name> <command> - Connect to MCP server
        /mcp disconnect <name> - Disconnect server
        /mcp tools - List available tools
        /mcp resources - List available resources
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    try:
        from ..core.mcp import get_mcp_manager
        mcp = get_mcp_manager()
        
        if not args:
            # Show status
            stats = mcp.get_stats() if hasattr(mcp, 'get_stats') else {}
            servers = mcp.list_servers() if hasattr(mcp, 'list_servers') else []
            
            text = (
                "🔌 **MCP (Model Context Protocol)**\n\n"
                f"Connected Servers: {len(servers)}\n"
            )
            
            if servers:
                text += "\n**Servers:**\n"
                for server in servers:
                    text += f"• {server}\n"
            
            text += (
                "\n**Commands:**\n"
                "`/mcp servers` - List servers\n"
                "`/mcp tools` - List tools\n"
                "`/mcp resources` - List resources\n"
                "`/mcp connect <name> <cmd>` - Connect server\n"
            )
            
            await update.message.reply_text(text, parse_mode="Markdown")
        
        elif args[0] == "servers":
            servers = mcp.list_servers() if hasattr(mcp, 'list_servers') else []
            
            if not servers:
                await update.message.reply_text("No MCP servers connected.")
                return
            
            text = "🔌 **Connected MCP Servers**\n\n"
            for server in servers:
                text += f"• `{server}`\n"
            
            await update.message.reply_text(text, parse_mode="Markdown")
        
        elif args[0] == "tools":
            tools = await mcp.list_tools() if hasattr(mcp, 'list_tools') else []
            
            if not tools:
                await update.message.reply_text("No MCP tools available.")
                return
            
            text = "🔧 **Available MCP Tools**\n\n"
            for tool in tools[:20]:
                name = tool.name if hasattr(tool, 'name') else str(tool)
                desc = tool.description[:50] if hasattr(tool, 'description') else ""
                text += f"• `{name}` - {desc}\n"
            
            if len(tools) > 20:
                text += f"\n... and {len(tools) - 20} more"
            
            await update.message.reply_text(text, parse_mode="Markdown")
        
        elif args[0] == "resources":
            resources = await mcp.list_resources() if hasattr(mcp, 'list_resources') else []
            
            if not resources:
                await update.message.reply_text("No MCP resources available.")
                return
            
            text = "📦 **Available MCP Resources**\n\n"
            for res in resources[:20]:
                name = res.name if hasattr(res, 'name') else str(res)
                text += f"• `{name}`\n"
            
            await update.message.reply_text(text, parse_mode="Markdown")
        
        elif args[0] == "connect" and len(args) >= 3:
            name = args[1]
            command = " ".join(args[2:])
            
            await update.message.reply_text(f"Connecting to MCP server `{name}`...", parse_mode="Markdown")
            
            success = await mcp.connect_server(name, command)
            
            if success:
                await update.message.reply_text(f"✅ Connected to MCP server `{name}`", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ Failed to connect to `{name}`", parse_mode="Markdown")
        
        elif args[0] == "disconnect" and len(args) >= 2:
            name = args[1]
            
            success = await mcp.disconnect_server(name) if hasattr(mcp, 'disconnect_server') else False
            
            if success:
                await update.message.reply_text(f"✅ Disconnected from `{name}`", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ Failed to disconnect from `{name}`", parse_mode="Markdown")
        
        else:
            await update.message.reply_text(
                "Usage:\n"
                "`/mcp` - Show status\n"
                "`/mcp servers` - List servers\n"
                "`/mcp tools` - List tools\n"
                "`/mcp connect <name> <command>` - Connect\n"
                "`/mcp disconnect <name>` - Disconnect",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"MCP command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# Workflow Handlers
# ============================================

async def workflow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /workflow command - Workflow management.
    
    Usage:
        /workflow - Show workflow status
        /workflow list - List available workflows
        /workflow run <name> - Run a workflow
        /workflow status <run_id> - Check workflow status
        /workflow cancel <run_id> - Cancel running workflow
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    try:
        from ..core.workflow import get_workflow_engine
        engine = get_workflow_engine()
        
        if not args:
            stats = engine.get_stats() if hasattr(engine, 'get_stats') else {}
            workflows = engine.list_workflows() if hasattr(engine, 'list_workflows') else []
            
            text = (
                "⚙️ **Workflow Engine**\n\n"
                f"Registered Workflows: {len(workflows)}\n"
                f"Active Runs: {stats.get('active_runs', 0)}\n"
            )
            
            text += (
                "\n**Commands:**\n"
                "`/workflow list` - List workflows\n"
                "`/workflow run <name>` - Run workflow\n"
                "`/workflow status <id>` - Check status\n"
            )
            
            await update.message.reply_text(text, parse_mode="Markdown")
        
        elif args[0] == "list":
            workflows = engine.list_workflows() if hasattr(engine, 'list_workflows') else []
            
            if not workflows:
                await update.message.reply_text("No workflows registered.")
                return
            
            text = "⚙️ **Available Workflows**\n\n"
            for wf in workflows:
                name = wf.name if hasattr(wf, 'name') else str(wf)
                desc = wf.description[:50] if hasattr(wf, 'description') else ""
                text += f"• `{name}` - {desc}\n"
            
            await update.message.reply_text(text, parse_mode="Markdown")
        
        elif args[0] == "run" and len(args) >= 2:
            name = args[1]
            
            await update.message.reply_text(f"Starting workflow `{name}`...", parse_mode="Markdown")
            
            run = await engine.run_workflow(name, context={"user_id": user_id})
            
            if run:
                run_id = run.id if hasattr(run, 'id') else str(run)
                await update.message.reply_text(
                    f"✅ Workflow started\n\nRun ID: `{run_id}`\n\nUse `/workflow status {run_id}` to check progress.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(f"❌ Failed to start workflow `{name}`", parse_mode="Markdown")
        
        elif args[0] == "status" and len(args) >= 2:
            run_id = args[1]
            
            status = engine.get_run_status(run_id) if hasattr(engine, 'get_run_status') else None
            
            if status:
                text = (
                    f"⚙️ **Workflow Status**\n\n"
                    f"Run ID: `{run_id}`\n"
                    f"Status: {status.get('status', 'unknown')}\n"
                    f"Progress: {status.get('progress', 0)}%\n"
                )
                await update.message.reply_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text(f"Workflow run `{run_id}` not found.", parse_mode="Markdown")
        
        else:
            await update.message.reply_text(
                "Usage:\n"
                "`/workflow list` - List workflows\n"
                "`/workflow run <name>` - Run workflow\n"
                "`/workflow status <id>` - Check status",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Workflow command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# Analytics Handlers
# ============================================

async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /analytics command - Usage analytics.
    
    Usage:
        /analytics - Show overview
        /analytics me - My usage stats
        /analytics daily - Daily statistics
        /analytics export - Export analytics data
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    try:
        from ..core.analytics import get_analytics
        analytics = get_analytics()
        
        if not args or args[0] == "overview":
            stats = analytics.get_overall_stats() if hasattr(analytics, 'get_overall_stats') else {}
            
            text = (
                "📊 **Analytics Overview**\n\n"
                f"Total Events: {stats.get('total_events', 0)}\n"
                f"Total Users: {stats.get('total_users', 0)}\n"
                f"Today's Events: {stats.get('today_events', 0)}\n"
            )
            
            if 'top_commands' in stats:
                text += "\n**Top Commands:**\n"
                for cmd, count in stats['top_commands'][:5]:
                    text += f"• `{cmd}`: {count}\n"
            
            text += (
                "\n**Commands:**\n"
                "`/analytics me` - Your stats\n"
                "`/analytics daily` - Daily stats\n"
                "`/analytics export` - Export data\n"
            )
            
            await update.message.reply_text(text, parse_mode="Markdown")
        
        elif args[0] == "me":
            user_stats = analytics.get_user_stats(user_id) if hasattr(analytics, 'get_user_stats') else None
            
            if user_stats:
                text = (
                    "📊 **Your Usage Statistics**\n\n"
                    f"Total Messages: {user_stats.total_messages}\n"
                    f"Total Commands: {user_stats.total_commands}\n"
                    f"LLM Requests: {user_stats.llm_requests}\n"
                    f"Total Tokens: {user_stats.total_tokens}\n"
                    f"Est. Cost: ${user_stats.estimated_cost:.4f}\n"
                )
                await update.message.reply_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text("No usage data found for your account.")
        
        elif args[0] == "daily":
            daily = analytics.get_daily_stats() if hasattr(analytics, 'get_daily_stats') else None
            
            if daily:
                text = (
                    f"📊 **Daily Statistics** ({daily.date})\n\n"
                    f"Events: {daily.total_events}\n"
                    f"Active Users: {daily.active_users}\n"
                    f"LLM Requests: {daily.llm_requests}\n"
                    f"Tokens Used: {daily.total_tokens}\n"
                    f"Est. Cost: ${daily.estimated_cost:.4f}\n"
                )
                await update.message.reply_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text("No daily statistics available.")
        
        elif args[0] == "export":
            format_type = args[1] if len(args) > 1 else "json"
            
            await update.message.reply_text("Exporting analytics data...")
            
            file_path = await analytics.export_to_file(format=format_type)
            
            if file_path:
                await update.message.reply_document(
                    document=open(file_path, 'rb'),
                    filename=f"analytics_export.{format_type}",
                    caption="📊 Analytics Export"
                )
            else:
                await update.message.reply_text("Failed to export analytics data.")
        
        else:
            await update.message.reply_text(
                "Usage:\n"
                "`/analytics` - Overview\n"
                "`/analytics me` - Your stats\n"
                "`/analytics daily` - Daily stats\n"
                "`/analytics export [json|csv]` - Export",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Analytics command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# Code Review Handlers
# ============================================

async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /review command - Code review.
    
    Usage:
        /review <file_path> - Review a file
        /review dir <directory> - Review directory
        /review diff - Review staged changes
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    if not args:
        await update.message.reply_text(
            "🔍 **Code Review**\n\n"
            "Usage:\n"
            "`/review <file>` - Review a file\n"
            "`/review dir <path>` - Review directory\n"
            "`/review diff` - Review git diff\n\n"
            "Example:\n"
            "`/review src/main.py`",
            parse_mode="Markdown"
        )
        return
    
    try:
        from ..core.code_review import get_code_reviewer
        reviewer = get_code_reviewer()
        
        workspace = os.getenv("CURSOR_WORKSPACE_PATH", os.getcwd())
        
        if args[0] == "dir" and len(args) >= 2:
            directory = args[1]
            full_path = os.path.join(workspace, directory) if not os.path.isabs(directory) else directory
            
            await update.message.reply_text(f"🔍 Reviewing directory `{directory}`...", parse_mode="Markdown")
            
            result = await reviewer.review_directory(full_path)
            
        elif args[0] == "diff":
            await update.message.reply_text("🔍 Reviewing git diff...", parse_mode="Markdown")
            
            # Get git diff
            import subprocess
            proc = subprocess.run(
                ["git", "diff", "--staged"],
                capture_output=True, text=True, cwd=workspace
            )
            diff_content = proc.stdout or ""
            
            if not diff_content:
                proc = subprocess.run(
                    ["git", "diff"],
                    capture_output=True, text=True, cwd=workspace
                )
                diff_content = proc.stdout
            
            if not diff_content:
                await update.message.reply_text("No changes to review.")
                return
            
            result = await reviewer.review_diff(diff_content)
            
        else:
            file_path = args[0]
            full_path = os.path.join(workspace, file_path) if not os.path.isabs(file_path) else file_path
            
            if not os.path.exists(full_path):
                await update.message.reply_text(f"File not found: `{file_path}`", parse_mode="Markdown")
                return
            
            await update.message.reply_text(f"🔍 Reviewing `{file_path}`...", parse_mode="Markdown")
            
            result = await reviewer.review_file(full_path)
        
        # Format result
        text = reviewer.format_findings(result, format="markdown")
        
        # Truncate if too long
        if len(text) > 4000:
            text = text[:3900] + "\n\n... (truncated)"
        
        await update.message.reply_text(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Review command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# Export Handlers
# ============================================

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /export command - Export conversation history.
    
    Usage:
        /export - Export in Markdown
        /export json - Export as JSON
        /export html - Export as HTML
    """
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    format_type = args[0] if args else "markdown"
    
    try:
        from ..core.conversation_export import get_exporter, ExportFormat
        
        exporter = get_exporter()
        
        format_map = {
            "json": ExportFormat.JSON,
            "markdown": ExportFormat.MARKDOWN,
            "md": ExportFormat.MARKDOWN,
            "html": ExportFormat.HTML,
            "txt": ExportFormat.TXT,
            "csv": ExportFormat.CSV,
        }
        
        export_format = format_map.get(format_type.lower(), ExportFormat.MARKDOWN)
        
        await update.message.reply_text(f"📦 Exporting conversation as {export_format.value}...")
        
        result = await exporter.export_to_file(
            user_id=user_id,
            chat_id=chat_id,
            format=export_format,
            output_dir="exports",
        )
        
        if result.success and result.file_path:
            ext_map = {
                ExportFormat.JSON: "json",
                ExportFormat.MARKDOWN: "md",
                ExportFormat.HTML: "html",
                ExportFormat.TXT: "txt",
                ExportFormat.CSV: "csv",
            }
            ext = ext_map.get(export_format, "txt")
            
            await update.message.reply_document(
                document=open(result.file_path, 'rb'),
                filename=f"conversation_export.{ext}",
                caption=f"📦 Exported {result.message_count} messages"
            )
        else:
            error_msg = result.error or "Unknown error"
            await update.message.reply_text(f"❌ Export failed: {error_msg}")
            
    except Exception as e:
        logger.error(f"Export command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# Auto-Documentation Handlers
# ============================================

async def docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /docs command - Generate documentation.
    
    Usage:
        /docs <file> - Generate docs for a file
        /docs api <dir> - Generate API docs
        /docs readme - Generate README
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    if not args:
        await update.message.reply_text(
            "📝 **Auto-Documentation**\n\n"
            "Usage:\n"
            "`/docs <file>` - Document a file\n"
            "`/docs api <dir>` - Generate API docs\n"
            "`/docs readme` - Generate README\n\n"
            "Example:\n"
            "`/docs src/core/rag.py`",
            parse_mode="Markdown"
        )
        return
    
    try:
        from ..core.auto_docs import get_doc_generator, DocFormat
        
        generator = get_doc_generator()
        workspace = os.getenv("CURSOR_WORKSPACE_PATH", os.getcwd())
        
        if args[0] == "api" and len(args) >= 2:
            directory = args[1]
            full_path = os.path.join(workspace, directory) if not os.path.isabs(directory) else directory
            
            await update.message.reply_text(f"📝 Generating API docs for `{directory}`...", parse_mode="Markdown")
            
            docs = await generator.generate_api_docs(full_path)
            
        elif args[0] == "readme":
            await update.message.reply_text("📝 Generating README...", parse_mode="Markdown")
            
            docs = await generator.generate_readme(workspace)
            
        else:
            file_path = args[0]
            full_path = os.path.join(workspace, file_path) if not os.path.isabs(file_path) else file_path
            
            if not os.path.exists(full_path):
                await update.message.reply_text(f"File not found: `{file_path}`", parse_mode="Markdown")
                return
            
            await update.message.reply_text(f"📝 Generating docs for `{file_path}`...", parse_mode="Markdown")
            
            docs = await generator.generate_module_docs(full_path)
        
        # Send as document if too long
        if len(docs) > 4000:
            # Write to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(docs)
                temp_path = f.name
            
            await update.message.reply_document(
                document=open(temp_path, 'rb'),
                filename="documentation.md",
                caption="📝 Generated Documentation"
            )
            os.unlink(temp_path)
        else:
            await update.message.reply_text(docs, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Docs command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# Handler Registration
# ============================================

def register_v04_handlers(application) -> None:
    """Register v0.4 feature handlers with the application."""
    # MCP
    application.add_handler(CommandHandler("mcp", mcp_command))
    
    # Workflow
    application.add_handler(CommandHandler("workflow", workflow_command))
    application.add_handler(CommandHandler("wf", workflow_command))
    
    # Analytics
    application.add_handler(CommandHandler("analytics", analytics_command))
    application.add_handler(CommandHandler("stats", analytics_command))
    
    # Code Review
    application.add_handler(CommandHandler("review", review_command))
    application.add_handler(CommandHandler("codereview", review_command))
    
    # Export
    application.add_handler(CommandHandler("export", export_command))
    
    # Auto-Documentation
    application.add_handler(CommandHandler("docs", docs_command))
    application.add_handler(CommandHandler("gendocs", docs_command))
    
    logger.info("v0.4 feature handlers registered")


__all__ = [
    "mcp_command",
    "workflow_command",
    "analytics_command",
    "review_command",
    "export_command",
    "docs_command",
    "register_v04_handlers",
]

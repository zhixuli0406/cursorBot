"""
RAG (Retrieval-Augmented Generation) Handlers for CursorBot

Provides Telegram commands for:
- /rag - Query with RAG
- /index - Index documents
- /search - Search indexed documents
- /ragstats - View RAG statistics
- /ragclear - Clear RAG index

Usage:
    /rag What is the main function of this project?
    /index /path/to/document.pdf
    /index_dir /path/to/docs
    /search keyword
"""

import os
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from ..core.rag import (
    get_rag_manager,
    reset_rag_manager,
    RAGConfig,
    ChunkingStrategy,
    EmbeddingProvider,
)
from ..utils.logger import logger
from ..utils.auth import is_authorized


# ============================================
# RAG Query Command
# ============================================

async def rag_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /rag command - Query with RAG.
    
    Usage:
        /rag <question>
        
    Example:
        /rag What is the main purpose of this project?
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    # Get question from command
    if not context.args:
        await update.message.reply_text(
            "**RAG Query**\n\n"
            "Usage: `/rag <question>`\n\n"
            "Example:\n"
            "`/rag What is the main function of this project?`\n\n"
            "This command searches indexed documents and generates an answer based on relevant content.\n\n"
            "Related commands:\n"
            "- `/index <file>` - Index a file\n"
            "- `/index_dir <directory>` - Index a directory\n"
            "- `/search <query>` - Search without generation\n"
            "- `/ragstats` - View statistics\n"
            "- `/ragclear` - Clear index",
            parse_mode="Markdown"
        )
        return
    
    question = " ".join(context.args)
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "Searching and generating answer..."
    )
    
    try:
        rag = get_rag_manager()
        
        # Check if there are indexed documents
        stats = rag.get_stats()
        if stats["indexed_documents"] == 0:
            await processing_msg.edit_text(
                "No documents indexed yet.\n\n"
                "Use `/index <file>` or `/index_dir <directory>` to index documents first.",
                parse_mode="Markdown"
            )
            return
        
        # Query with RAG
        response = await rag.query(question)
        
        # Format response
        answer = response.answer
        
        # Add sources if available
        if response.sources:
            sources_text = "\n\n**Sources:**\n"
            for i, source in enumerate(response.sources[:3]):
                source_name = source.document.metadata.get("filename", 
                    source.document.metadata.get("source", "Unknown"))
                score = f"{source.score:.2f}"
                sources_text += f"{i+1}. {source_name} (relevance: {score})\n"
            answer += sources_text
        
        # Truncate if too long
        if len(answer) > 4000:
            answer = answer[:4000] + "\n\n...(truncated)"
        
        await processing_msg.edit_text(answer, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        await processing_msg.edit_text(f"Error: {str(e)}")


# ============================================
# Index File Command
# ============================================

async def index_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /index command - Index a file.
    
    Usage:
        /index <file_path>
        
    Example:
        /index /path/to/document.pdf
        /index README.md
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Index File**\n\n"
            "Usage: `/index <file_path>`\n\n"
            "Supported formats:\n"
            "- Text: `.txt`, `.log`\n"
            "- Markdown: `.md`, `.markdown`\n"
            "- Code: `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, etc.\n"
            "- PDF: `.pdf`\n"
            "- JSON: `.json`, `.jsonl`\n\n"
            "Example:\n"
            "`/index /path/to/document.pdf`\n"
            "`/index README.md`",
            parse_mode="Markdown"
        )
        return
    
    file_path = " ".join(context.args)
    
    # Resolve relative paths
    if not os.path.isabs(file_path):
        workspace = os.getenv("CURSOR_WORKSPACE_PATH", os.getcwd())
        file_path = os.path.join(workspace, file_path)
    
    # Check if file exists
    if not os.path.exists(file_path):
        await update.message.reply_text(f"File not found: `{file_path}`", parse_mode="Markdown")
        return
    
    processing_msg = await update.message.reply_text(
        f"Indexing `{os.path.basename(file_path)}`..."
    )
    
    try:
        rag = get_rag_manager()
        chunks = await rag.index_file(file_path)
        
        await processing_msg.edit_text(
            f"Successfully indexed `{os.path.basename(file_path)}`\n"
            f"Created {chunks} chunks.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Index file error: {e}")
        await processing_msg.edit_text(f"Error indexing file: {str(e)}")


# ============================================
# Index Directory Command
# ============================================

async def index_dir_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /index_dir command - Index a directory.
    
    Usage:
        /index_dir <directory_path>
        
    Example:
        /index_dir /path/to/docs
        /index_dir src/
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Index Directory**\n\n"
            "Usage: `/index_dir <directory_path>`\n\n"
            "Options:\n"
            "- Recursively indexes all supported files\n"
            "- Ignores common patterns (`.git`, `node_modules`, etc.)\n\n"
            "Example:\n"
            "`/index_dir /path/to/docs`\n"
            "`/index_dir src/`",
            parse_mode="Markdown"
        )
        return
    
    dir_path = " ".join(context.args)
    
    # Resolve relative paths
    if not os.path.isabs(dir_path):
        workspace = os.getenv("CURSOR_WORKSPACE_PATH", os.getcwd())
        dir_path = os.path.join(workspace, dir_path)
    
    # Check if directory exists
    if not os.path.isdir(dir_path):
        await update.message.reply_text(f"Directory not found: `{dir_path}`", parse_mode="Markdown")
        return
    
    processing_msg = await update.message.reply_text(
        f"Indexing directory `{os.path.basename(dir_path)}`...\nThis may take a while."
    )
    
    try:
        rag = get_rag_manager()
        chunks = await rag.index_directory(dir_path)
        
        await processing_msg.edit_text(
            f"Successfully indexed directory `{os.path.basename(dir_path)}`\n"
            f"Created {chunks} chunks total.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Index directory error: {e}")
        await processing_msg.edit_text(f"Error indexing directory: {str(e)}")


# ============================================
# Index URL Command
# ============================================

async def index_url_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /index_url command - Index content from a URL.
    
    Usage:
        /index_url <url>
        
    Example:
        /index_url https://example.com/docs/guide.html
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Index URL**\n\n"
            "Usage: `/index_url <url>`\n\n"
            "Example:\n"
            "`/index_url https://example.com/docs/guide.html`",
            parse_mode="Markdown"
        )
        return
    
    url = context.args[0]
    
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("Please provide a valid URL starting with http:// or https://")
        return
    
    processing_msg = await update.message.reply_text(f"Indexing URL: {url}...")
    
    try:
        rag = get_rag_manager()
        chunks = await rag.index_url(url)
        
        await processing_msg.edit_text(
            f"Successfully indexed URL\n"
            f"Created {chunks} chunks.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Index URL error: {e}")
        await processing_msg.edit_text(f"Error indexing URL: {str(e)}")


# ============================================
# Search Command
# ============================================

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /search command - Search indexed documents.
    
    Usage:
        /search <query>
        
    Example:
        /search authentication
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Search Documents**\n\n"
            "Usage: `/search <query>`\n\n"
            "Example:\n"
            "`/search authentication`\n"
            "`/search how to configure`\n\n"
            "This searches indexed documents without generating an answer.\n"
            "Use `/rag` for question answering.",
            parse_mode="Markdown"
        )
        return
    
    query = " ".join(context.args)
    
    processing_msg = await update.message.reply_text("Searching...")
    
    try:
        rag = get_rag_manager()
        
        # Check if there are indexed documents
        stats = rag.get_stats()
        if stats["indexed_documents"] == 0:
            await processing_msg.edit_text(
                "No documents indexed yet.\n\n"
                "Use `/index <file>` or `/index_dir <directory>` to index documents first.",
                parse_mode="Markdown"
            )
            return
        
        results = await rag.search(query, top_k=5)
        
        if not results:
            await processing_msg.edit_text(
                f"No results found for: `{query}`\n\n"
                "Try a different search term or lower the similarity threshold.",
                parse_mode="Markdown"
            )
            return
        
        # Format results
        response = f"**Search Results for:** `{query}`\n\n"
        
        for i, result in enumerate(results):
            source = result.document.metadata.get("filename",
                result.document.metadata.get("source", "Unknown"))
            score = f"{result.score:.2f}"
            
            # Truncate content
            content = result.document.content[:200]
            if len(result.document.content) > 200:
                content += "..."
            
            # Escape markdown special characters
            content = content.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
            
            response += f"**{i+1}. {source}** (relevance: {score})\n"
            response += f"{content}\n\n"
        
        await processing_msg.edit_text(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        await processing_msg.edit_text(f"Error: {str(e)}")


# ============================================
# RAG Stats Command
# ============================================

async def ragstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /ragstats command - View RAG statistics.
    
    Usage:
        /ragstats
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    try:
        rag = get_rag_manager()
        stats = rag.get_stats()
        
        config = stats.get("config", {})
        
        response = "**RAG System Statistics**\n\n"
        response += f"**Indexed Documents:** {stats.get('indexed_documents', 0)}\n"
        response += f"**Total Indexed:** {stats.get('total_indexed', 0)}\n"
        response += f"**Total Queries:** {stats.get('total_queries', 0)}\n\n"
        
        response += "**Configuration:**\n"
        response += f"- Chunk Size: {config.get('chunk_size', 'N/A')}\n"
        response += f"- Chunk Overlap: {config.get('chunk_overlap', 'N/A')}\n"
        response += f"- Chunking Strategy: {config.get('chunking_strategy', 'N/A')}\n"
        response += f"- Embedding Provider: {config.get('embedding_provider', 'N/A')}\n"
        response += f"- Embedding Model: {config.get('embedding_model', 'N/A')}\n"
        response += f"- Top K: {config.get('top_k', 'N/A')}\n"
        response += f"- Similarity Threshold: {config.get('similarity_threshold', 'N/A')}\n"
        
        await update.message.reply_text(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"RAG stats error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


# ============================================
# RAG Clear Command
# ============================================

async def ragclear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /ragclear command - Clear RAG index.
    
    Usage:
        /ragclear
        /ragclear confirm
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    # Check for confirmation
    if not context.args or context.args[0].lower() != "confirm":
        rag = get_rag_manager()
        stats = rag.get_stats()
        
        await update.message.reply_text(
            f"**Warning: Clear RAG Index**\n\n"
            f"This will delete all {stats.get('indexed_documents', 0)} indexed documents.\n\n"
            f"To confirm, run:\n`/ragclear confirm`",
            parse_mode="Markdown"
        )
        return
    
    try:
        rag = get_rag_manager()
        await rag.clear()
        
        await update.message.reply_text("RAG index cleared successfully.")
        
    except Exception as e:
        logger.error(f"RAG clear error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


# ============================================
# RAG Config Command
# ============================================

async def ragconfig_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /ragconfig command - Configure RAG settings.
    
    Usage:
        /ragconfig
        /ragconfig chunk_size 1000
        /ragconfig top_k 10
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**RAG Configuration**\n\n"
            "Usage: `/ragconfig <setting> <value>`\n\n"
            "Available settings:\n"
            "- `chunk_size` - Size of text chunks (default: 500)\n"
            "- `chunk_overlap` - Overlap between chunks (default: 50)\n"
            "- `top_k` - Number of results to retrieve (default: 5)\n"
            "- `similarity_threshold` - Minimum similarity score (default: 0.7)\n\n"
            "Example:\n"
            "`/ragconfig chunk_size 1000`\n"
            "`/ragconfig top_k 10`\n\n"
            "Note: Changes apply to new operations. Re-index to apply chunk settings.",
            parse_mode="Markdown"
        )
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Please provide both setting name and value.")
        return
    
    setting = context.args[0].lower()
    value = context.args[1]
    
    try:
        rag = get_rag_manager()
        
        if setting == "chunk_size":
            rag.config.chunk_size = int(value)
            msg = f"Chunk size set to {value}"
        elif setting == "chunk_overlap":
            rag.config.chunk_overlap = int(value)
            msg = f"Chunk overlap set to {value}"
        elif setting == "top_k":
            rag.config.top_k = int(value)
            msg = f"Top K set to {value}"
        elif setting == "similarity_threshold":
            rag.config.similarity_threshold = float(value)
            msg = f"Similarity threshold set to {value}"
        else:
            await update.message.reply_text(f"Unknown setting: `{setting}`", parse_mode="Markdown")
            return
        
        await update.message.reply_text(f"Configuration updated: {msg}")
        
    except ValueError as e:
        await update.message.reply_text(f"Invalid value: {str(e)}")
    except Exception as e:
        logger.error(f"RAG config error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


# ============================================
# Index Text Command (for inline text)
# ============================================

async def index_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /index_text command - Index inline text.
    
    Usage:
        /index_text <text content>
        
    Example:
        /index_text This is some important information about the project.
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Index Text**\n\n"
            "Usage: `/index_text <text content>`\n\n"
            "Example:\n"
            "`/index_text This is some important information about the project.`",
            parse_mode="Markdown"
        )
        return
    
    text = " ".join(context.args)
    
    processing_msg = await update.message.reply_text("Indexing text...")
    
    try:
        rag = get_rag_manager()
        chunks = await rag.index_text(text, metadata={"source": "manual", "user": user_id})
        
        await processing_msg.edit_text(
            f"Successfully indexed text.\n"
            f"Created {chunks} chunks.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Index text error: {e}")
        await processing_msg.edit_text(f"Error: {str(e)}")


# ============================================
# Handler Registration
# ============================================

def register_rag_handlers(application) -> None:
    """Register RAG command handlers with the application."""
    from telegram.ext import CommandHandler
    
    application.add_handler(CommandHandler("rag", rag_command))
    application.add_handler(CommandHandler("index", index_command))
    application.add_handler(CommandHandler("index_dir", index_dir_command))
    application.add_handler(CommandHandler("index_url", index_url_command))
    application.add_handler(CommandHandler("index_text", index_text_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("ragstats", ragstats_command))
    application.add_handler(CommandHandler("ragclear", ragclear_command))
    application.add_handler(CommandHandler("ragconfig", ragconfig_command))
    
    logger.info("RAG handlers registered")


__all__ = [
    "rag_command",
    "index_command",
    "index_dir_command",
    "index_url_command",
    "index_text_command",
    "search_command",
    "ragstats_command",
    "ragclear_command",
    "ragconfig_command",
    "register_rag_handlers",
]

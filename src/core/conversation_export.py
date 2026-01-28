"""
Conversation Export for CursorBot

Export conversation history in various formats.

Features:
- Export to JSON, Markdown, HTML, PDF
- Filter by date, user, chat
- Include/exclude system messages
- Attachment handling
- Privacy options (redact sensitive data)

Usage:
    from src.core.conversation_export import get_exporter, ExportFormat
    
    exporter = get_exporter()
    
    # Export conversation
    result = await exporter.export(
        user_id="123",
        format=ExportFormat.MARKDOWN,
        start_date=datetime(2025, 1, 1),
    )
    
    # Export to file
    file_path = await exporter.export_to_file(
        user_id="123",
        format=ExportFormat.HTML,
        output_dir="exports/",
    )
"""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Union

from ..utils.logger import logger


# ============================================
# Export Types
# ============================================

class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    TXT = "txt"
    CSV = "csv"


@dataclass
class ExportMessage:
    """A message in the export."""
    id: str
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    user_name: Optional[str] = None
    attachments: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "user_name": self.user_name,
            "attachments": self.attachments,
            "metadata": self.metadata,
        }


@dataclass
class ExportConfig:
    """Configuration for export."""
    # Filters
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_system: bool = False
    include_attachments: bool = True
    
    # Privacy
    redact_user_ids: bool = False
    redact_emails: bool = True
    redact_phone_numbers: bool = True
    redact_api_keys: bool = True
    
    # Formatting
    include_metadata: bool = False
    include_timestamps: bool = True
    timezone: str = "UTC"
    
    # HTML options
    html_theme: str = "light"  # light, dark
    html_title: str = "Conversation Export"


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    format: ExportFormat
    content: str = ""
    file_path: Optional[str] = None
    message_count: int = 0
    size_bytes: int = 0
    exported_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "format": self.format.value,
            "file_path": self.file_path,
            "message_count": self.message_count,
            "size_bytes": self.size_bytes,
            "exported_at": self.exported_at.isoformat(),
            "error": self.error,
        }


# ============================================
# Privacy Redactor
# ============================================

class PrivacyRedactor:
    """Redacts sensitive information from text."""
    
    PATTERNS = {
        "email": (r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]'),
        "phone": (r'\+?[\d\s\-\(\)]{10,}', '[PHONE]'),
        "api_key": (r'(?:sk-|api[_-]?key[=:]?\s*)[a-zA-Z0-9\-_]{20,}', '[API_KEY]'),
        "credit_card": (r'\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}', '[CREDIT_CARD]'),
        "ssn": (r'\d{3}[\s\-]?\d{2}[\s\-]?\d{4}', '[SSN]'),
        "ip_address": (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP]'),
        "user_id": (r'user[_-]?id[=:]?\s*\d+', '[USER_ID]'),
    }
    
    def redact(self, text: str, config: ExportConfig) -> str:
        """Redact sensitive information based on config."""
        result = text
        
        if config.redact_emails:
            result = re.sub(self.PATTERNS["email"][0], self.PATTERNS["email"][1], result, flags=re.IGNORECASE)
        
        if config.redact_phone_numbers:
            result = re.sub(self.PATTERNS["phone"][0], self.PATTERNS["phone"][1], result)
        
        if config.redact_api_keys:
            result = re.sub(self.PATTERNS["api_key"][0], self.PATTERNS["api_key"][1], result, flags=re.IGNORECASE)
        
        if config.redact_user_ids:
            result = re.sub(self.PATTERNS["user_id"][0], self.PATTERNS["user_id"][1], result, flags=re.IGNORECASE)
        
        return result


# ============================================
# Format Exporters
# ============================================

class BaseExporter:
    """Base class for format exporters."""
    
    def __init__(self, config: ExportConfig = None):
        self.config = config or ExportConfig()
        self._redactor = PrivacyRedactor()
    
    def export(self, messages: list[ExportMessage]) -> str:
        """Export messages to string."""
        raise NotImplementedError
    
    def _redact_message(self, message: ExportMessage) -> ExportMessage:
        """Apply privacy redaction to a message."""
        return ExportMessage(
            id=message.id,
            role=message.role,
            content=self._redactor.redact(message.content, self.config),
            timestamp=message.timestamp,
            user_name=message.user_name if not self.config.redact_user_ids else "[USER]",
            attachments=message.attachments if self.config.include_attachments else [],
            metadata=message.metadata if self.config.include_metadata else {},
        )


class JSONExporter(BaseExporter):
    """Export to JSON format."""
    
    def export(self, messages: list[ExportMessage]) -> str:
        processed = [self._redact_message(m).to_dict() for m in messages]
        return json.dumps({
            "exported_at": datetime.now().isoformat(),
            "message_count": len(processed),
            "messages": processed,
        }, indent=2, ensure_ascii=False)


class MarkdownExporter(BaseExporter):
    """Export to Markdown format."""
    
    def export(self, messages: list[ExportMessage]) -> str:
        lines = [
            "# Conversation Export",
            "",
            f"*Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            f"*Messages: {len(messages)}*",
            "",
            "---",
            "",
        ]
        
        current_date = None
        
        for msg in messages:
            msg = self._redact_message(msg)
            
            # Add date separator
            msg_date = msg.timestamp.strftime("%Y-%m-%d")
            if msg_date != current_date:
                current_date = msg_date
                lines.append(f"## {msg_date}")
                lines.append("")
            
            # Format message
            role_icon = {
                "user": "👤",
                "assistant": "🤖",
                "system": "⚙️",
            }.get(msg.role, "•")
            
            timestamp = ""
            if self.config.include_timestamps:
                timestamp = f" *{msg.timestamp.strftime('%H:%M:%S')}*"
            
            user_str = ""
            if msg.user_name:
                user_str = f" **{msg.user_name}**"
            
            lines.append(f"### {role_icon}{user_str}{timestamp}")
            lines.append("")
            lines.append(msg.content)
            lines.append("")
            
            # Attachments
            if msg.attachments:
                lines.append("**Attachments:**")
                for att in msg.attachments:
                    att_type = att.get("type", "file")
                    att_name = att.get("name", "attachment")
                    lines.append(f"- [{att_type}] {att_name}")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)


class HTMLExporter(BaseExporter):
    """Export to HTML format."""
    
    def export(self, messages: list[ExportMessage]) -> str:
        is_dark = self.config.html_theme == "dark"
        
        # CSS styles
        bg_color = "#1a1a2e" if is_dark else "#ffffff"
        text_color = "#eaeaea" if is_dark else "#333333"
        user_bg = "#16213e" if is_dark else "#e3f2fd"
        assistant_bg = "#0f3460" if is_dark else "#f5f5f5"
        border_color = "#e94560" if is_dark else "#2196f3"
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.html_title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background-color: {bg_color};
            color: {text_color};
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            padding: 20px 0;
            border-bottom: 2px solid {border_color};
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: {border_color};
        }}
        .stats {{
            color: #888;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        .date-separator {{
            text-align: center;
            padding: 10px 0;
            color: #888;
            font-weight: bold;
        }}
        .message {{
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
            max-width: 85%;
        }}
        .message.user {{
            background-color: {user_bg};
            margin-left: auto;
            border-left: 4px solid {border_color};
        }}
        .message.assistant {{
            background-color: {assistant_bg};
            border-left: 4px solid #4caf50;
        }}
        .message.system {{
            background-color: #333;
            color: #999;
            font-style: italic;
            max-width: 100%;
            text-align: center;
        }}
        .message-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 0.85em;
            color: #888;
        }}
        .role-icon {{
            margin-right: 5px;
        }}
        .content {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .content code {{
            background: rgba(0,0,0,0.2);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Fira Code', 'Consolas', monospace;
        }}
        .content pre {{
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 10px 0;
        }}
        .attachments {{
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid rgba(128,128,128,0.3);
            font-size: 0.85em;
        }}
        .attachment {{
            display: inline-block;
            background: rgba(0,0,0,0.2);
            padding: 3px 8px;
            border-radius: 3px;
            margin: 2px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{self.config.html_title}</h1>
            <div class="stats">
                Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
                Messages: {len(messages)}
            </div>
        </div>
"""
        
        current_date = None
        
        for msg in messages:
            msg = self._redact_message(msg)
            
            # Date separator
            msg_date = msg.timestamp.strftime("%Y-%m-%d")
            if msg_date != current_date:
                current_date = msg_date
                html += f'        <div class="date-separator">{msg_date}</div>\n'
            
            # Role icon
            role_icon = {
                "user": "👤",
                "assistant": "🤖",
                "system": "⚙️",
            }.get(msg.role, "•")
            
            # Escape HTML in content
            content = self._escape_html(msg.content)
            # Convert markdown code blocks
            content = re.sub(r'```(\w*)\n(.*?)```', r'<pre><code>\2</code></pre>', content, flags=re.DOTALL)
            content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
            
            timestamp = msg.timestamp.strftime('%H:%M:%S') if self.config.include_timestamps else ""
            user_name = msg.user_name or msg.role.capitalize()
            
            html += f"""        <div class="message {msg.role}">
            <div class="message-header">
                <span><span class="role-icon">{role_icon}</span> {user_name}</span>
                <span>{timestamp}</span>
            </div>
            <div class="content">{content}</div>
"""
            
            # Attachments
            if msg.attachments:
                html += '            <div class="attachments">\n'
                for att in msg.attachments:
                    att_type = att.get("type", "file")
                    att_name = att.get("name", "attachment")
                    html += f'                <span class="attachment">📎 {att_type}: {att_name}</span>\n'
                html += '            </div>\n'
            
            html += '        </div>\n'
        
        html += """    </div>
</body>
</html>"""
        
        return html
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("\n", "<br>")
        )


class TxtExporter(BaseExporter):
    """Export to plain text format."""
    
    def export(self, messages: list[ExportMessage]) -> str:
        lines = [
            "=" * 60,
            "CONVERSATION EXPORT",
            f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Messages: {len(messages)}",
            "=" * 60,
            "",
        ]
        
        for msg in messages:
            msg = self._redact_message(msg)
            
            timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.config.include_timestamps else ""
            user_name = msg.user_name or msg.role.upper()
            
            lines.append("-" * 40)
            lines.append(f"[{user_name}] {timestamp}")
            lines.append("-" * 40)
            lines.append(msg.content)
            lines.append("")
        
        return "\n".join(lines)


class CSVExporter(BaseExporter):
    """Export to CSV format."""
    
    def export(self, messages: list[ExportMessage]) -> str:
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["timestamp", "role", "user_name", "content"])
        
        for msg in messages:
            msg = self._redact_message(msg)
            writer.writerow([
                msg.timestamp.isoformat(),
                msg.role,
                msg.user_name or "",
                msg.content,
            ])
        
        return output.getvalue()


# ============================================
# Conversation Export Manager
# ============================================

class ConversationExporter:
    """Main conversation export manager."""
    
    def __init__(self, config: ExportConfig = None):
        self.config = config or ExportConfig()
        
        self._exporters = {
            ExportFormat.JSON: JSONExporter,
            ExportFormat.MARKDOWN: MarkdownExporter,
            ExportFormat.HTML: HTMLExporter,
            ExportFormat.TXT: TxtExporter,
            ExportFormat.CSV: CSVExporter,
        }
    
    async def export(
        self,
        user_id: str = None,
        chat_id: str = None,
        format: ExportFormat = ExportFormat.MARKDOWN,
        config: ExportConfig = None,
    ) -> ExportResult:
        """Export conversation history."""
        config = config or self.config
        
        try:
            # Fetch messages from context manager
            messages = await self._fetch_messages(user_id, chat_id, config)
            
            # Filter messages
            messages = self._filter_messages(messages, config)
            
            # Export
            exporter_class = self._exporters.get(format, MarkdownExporter)
            exporter = exporter_class(config)
            content = exporter.export(messages)
            
            return ExportResult(
                success=True,
                format=format,
                content=content,
                message_count=len(messages),
                size_bytes=len(content.encode('utf-8')),
            )
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ExportResult(
                success=False,
                format=format,
                error=str(e),
            )
    
    async def export_to_file(
        self,
        user_id: str = None,
        chat_id: str = None,
        format: ExportFormat = ExportFormat.MARKDOWN,
        output_dir: str = "exports",
        filename: str = None,
        config: ExportConfig = None,
    ) -> ExportResult:
        """Export conversation to a file."""
        result = await self.export(user_id, chat_id, format, config)
        
        if not result.success:
            return result
        
        try:
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                user_part = f"_user{user_id}" if user_id else ""
                chat_part = f"_chat{chat_id}" if chat_id else ""
                ext = self._get_extension(format)
                filename = f"conversation{user_part}{chat_part}_{timestamp}.{ext}"
            
            # Write file
            file_path = output_path / filename
            file_path.write_text(result.content, encoding='utf-8')
            
            result.file_path = str(file_path)
            logger.info(f"Exported conversation to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to write export file: {e}")
            result.success = False
            result.error = str(e)
        
        return result
    
    async def _fetch_messages(
        self,
        user_id: str = None,
        chat_id: str = None,
        config: ExportConfig = None,
    ) -> list[ExportMessage]:
        """Fetch messages from storage."""
        messages = []
        
        try:
            # Try to get from context manager
            from .context import get_context_manager
            
            ctx_manager = get_context_manager()
            
            if user_id and chat_id:
                ctx = ctx_manager.get_context(user_id, chat_id)
                if ctx:
                    for i, msg in enumerate(ctx.messages):
                        messages.append(ExportMessage(
                            id=f"msg_{i}",
                            role=msg.get("role", "user"),
                            content=msg.get("content", ""),
                            timestamp=datetime.now() - timedelta(minutes=len(ctx.messages) - i),
                            user_name=msg.get("name"),
                        ))
            
            # Try to get from session manager
            if not messages:
                from .session import get_session_manager
                
                session_mgr = get_session_manager()
                
                if user_id:
                    sessions = session_mgr.list_user_sessions(user_id)
                    for session in sessions:
                        for i, msg in enumerate(session.messages):
                            messages.append(ExportMessage(
                                id=f"msg_{session.session_key}_{i}",
                                role=msg.get("role", "user"),
                                content=msg.get("content", ""),
                                timestamp=session.created_at + timedelta(minutes=i),
                                user_name=msg.get("name"),
                            ))
            
            # Try to get from RAG (stored conversations)
            if not messages:
                from .rag import get_rag_manager
                
                rag = get_rag_manager()
                
                # Search for conversation records
                results = await rag.search(
                    query=f"user_id:{user_id}" if user_id else "type:conversation",
                    top_k=100,
                )
                
                for r in results:
                    messages.append(ExportMessage(
                        id=r.doc_id,
                        role="conversation",
                        content=r.content,
                        timestamp=datetime.now(),
                        metadata=r.metadata,
                    ))
                    
        except Exception as e:
            logger.warning(f"Failed to fetch messages from storage: {e}")
        
        return messages
    
    def _filter_messages(
        self,
        messages: list[ExportMessage],
        config: ExportConfig,
    ) -> list[ExportMessage]:
        """Filter messages based on config."""
        filtered = []
        
        for msg in messages:
            # Filter by date
            if config.start_date and msg.timestamp < config.start_date:
                continue
            if config.end_date and msg.timestamp > config.end_date:
                continue
            
            # Filter system messages
            if not config.include_system and msg.role == "system":
                continue
            
            filtered.append(msg)
        
        # Sort by timestamp
        filtered.sort(key=lambda m: m.timestamp)
        
        return filtered
    
    def _get_extension(self, format: ExportFormat) -> str:
        """Get file extension for format."""
        ext_map = {
            ExportFormat.JSON: "json",
            ExportFormat.MARKDOWN: "md",
            ExportFormat.HTML: "html",
            ExportFormat.TXT: "txt",
            ExportFormat.CSV: "csv",
        }
        return ext_map.get(format, "txt")
    
    def list_formats(self) -> list[dict]:
        """List available export formats."""
        return [
            {"id": "json", "name": "JSON", "description": "Machine-readable JSON format"},
            {"id": "markdown", "name": "Markdown", "description": "Human-readable Markdown format"},
            {"id": "html", "name": "HTML", "description": "Styled HTML webpage"},
            {"id": "txt", "name": "Plain Text", "description": "Simple text format"},
            {"id": "csv", "name": "CSV", "description": "Spreadsheet-compatible CSV"},
        ]


# ============================================
# Global Instance
# ============================================

_exporter: Optional[ConversationExporter] = None


def get_exporter(config: ExportConfig = None) -> ConversationExporter:
    """Get the global conversation exporter instance."""
    global _exporter
    
    if _exporter is None:
        _exporter = ConversationExporter(config)
        logger.info("Conversation exporter initialized")
    
    return _exporter


def reset_exporter() -> None:
    """Reset the exporter instance."""
    global _exporter
    _exporter = None


__all__ = [
    # Types
    "ExportFormat",
    "ExportMessage",
    "ExportConfig",
    "ExportResult",
    # Redactor
    "PrivacyRedactor",
    # Exporters
    "BaseExporter",
    "JSONExporter",
    "MarkdownExporter",
    "HTMLExporter",
    "TxtExporter",
    "CSVExporter",
    # Manager
    "ConversationExporter",
    "get_exporter",
    "reset_exporter",
]

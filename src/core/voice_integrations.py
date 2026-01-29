"""
Voice Integrations for CursorBot v1.1

Provides voice-controlled integrations:
- File operations (create, delete, rename, move)
- Clipboard operations (copy, paste, clear)
- Weather queries
- Calendar integration
- Translation
- Voice search

Usage:
    from src.core.voice_integrations import (
        FileOperationHandler,
        ClipboardHandler,
        WeatherHandler,
        CalendarVoiceHandler,
        TranslationHandler,
        VoiceSearchHandler,
    )
"""

import os
import asyncio
import subprocess
import platform
import re
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil

from ..utils.logger import logger
from .voice_assistant import Intent, IntentCategory
from .voice_commands import CommandResult, CommandStatus, CommandHandler


# ============================================
# File Operations
# ============================================

class FileOperationType(Enum):
    """File operation types."""
    CREATE = "create"
    DELETE = "delete"
    RENAME = "rename"
    MOVE = "move"
    COPY = "copy"
    OPEN = "open"
    LIST = "list"


@dataclass
class FileOperation:
    """File operation details."""
    operation: FileOperationType
    source: Optional[str] = None
    destination: Optional[str] = None
    content: Optional[str] = None


class FileOperationHandler(CommandHandler):
    """Handle file operation voice commands."""
    
    OPERATION_PATTERNS = {
        FileOperationType.CREATE: [
            r"新建|建立|create|new|創建",
            r"檔案|file|文件",
        ],
        FileOperationType.DELETE: [
            r"刪除|移除|delete|remove|rm",
        ],
        FileOperationType.RENAME: [
            r"重新命名|改名|rename|重命名",
        ],
        FileOperationType.MOVE: [
            r"移動|move|搬移",
        ],
        FileOperationType.COPY: [
            r"複製|copy|拷貝",
        ],
        FileOperationType.OPEN: [
            r"打開|開啟|open|查看|view",
        ],
        FileOperationType.LIST: [
            r"列出|list|顯示|show|ls",
        ],
    }
    
    def __init__(self, workspace_path: Optional[str] = None):
        self._workspace = workspace_path or os.getcwd()
        self._system = platform.system()
    
    def can_handle(self, intent: Intent) -> bool:
        text = intent.raw_text.lower()
        
        # Check for file-related keywords
        file_keywords = ["檔案", "file", "文件", "資料夾", "folder", "目錄", "directory"]
        has_file_keyword = any(k in text for k in file_keywords)
        
        # Check for operation keywords
        for op_patterns in self.OPERATION_PATTERNS.values():
            if any(re.search(p, text, re.IGNORECASE) for p in op_patterns):
                if has_file_keyword or intent.category == IntentCategory.COMMAND:
                    return True
        
        return False
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        """Execute file operation."""
        text = intent.raw_text
        
        # Determine operation type
        operation = self._detect_operation(text)
        if not operation:
            return CommandResult(
                status=CommandStatus.FAILED,
                response_text="無法識別檔案操作類型。"
            )
        
        # Extract file name/path
        file_info = self._extract_file_info(text, operation)
        
        if operation == FileOperationType.CREATE:
            return await self._create_file(file_info)
        elif operation == FileOperationType.DELETE:
            return await self._delete_file(file_info)
        elif operation == FileOperationType.RENAME:
            return await self._rename_file(file_info)
        elif operation == FileOperationType.OPEN:
            return await self._open_file(file_info)
        elif operation == FileOperationType.LIST:
            return await self._list_files(file_info)
        elif operation == FileOperationType.COPY:
            return await self._copy_file(file_info)
        elif operation == FileOperationType.MOVE:
            return await self._move_file(file_info)
        
        return CommandResult(
            status=CommandStatus.FAILED,
            response_text="不支援的檔案操作。"
        )
    
    def _detect_operation(self, text: str) -> Optional[FileOperationType]:
        """Detect operation type from text."""
        text_lower = text.lower()
        
        for op_type, patterns in self.OPERATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return op_type
        
        return None
    
    def _extract_file_info(self, text: str, operation: FileOperationType) -> FileOperation:
        """Extract file information from text."""
        # Try to extract filename
        filename = None
        destination = None
        
        # Common patterns for filename extraction
        patterns = [
            r"(?:叫做|名為|叫|named?|called?)\s*[「「]?([^」」\s]+)[」」]?",
            r"(?:檔案|file|文件)\s*[「「]?([^」」\s]+)[」」]?",
            r"[「「]([^」」]+)[」」]",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                filename = match.group(1)
                break
        
        # For rename, try to extract new name
        if operation == FileOperationType.RENAME:
            rename_match = re.search(r"改(?:為|成|名為)\s*[「「]?([^」」\s]+)[」」]?", text)
            if rename_match:
                destination = rename_match.group(1)
        
        return FileOperation(
            operation=operation,
            source=filename,
            destination=destination
        )
    
    async def _create_file(self, info: FileOperation) -> CommandResult:
        """Create a new file."""
        if not info.source:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請問要建立什麼名稱的檔案？"
            )
        
        filepath = Path(self._workspace) / info.source
        
        try:
            # Check if parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file
            filepath.touch()
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text=f"已建立檔案 {info.source}。"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"建立檔案失敗：{e}"
            )
    
    async def _delete_file(self, info: FileOperation) -> CommandResult:
        """Delete a file."""
        if not info.source:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請問要刪除哪個檔案？"
            )
        
        filepath = Path(self._workspace) / info.source
        
        if not filepath.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                response_text=f"找不到檔案 {info.source}。"
            )
        
        # This is a dangerous operation - should require confirmation
        return CommandResult(
            status=CommandStatus.REQUIRES_CONFIRMATION,
            response_text=f"確定要刪除 {info.source} 嗎？",
            data={"file": str(filepath), "action": "delete"}
        )
    
    async def _rename_file(self, info: FileOperation) -> CommandResult:
        """Rename a file."""
        if not info.source or not info.destination:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請提供原檔名和新檔名。"
            )
        
        source_path = Path(self._workspace) / info.source
        dest_path = Path(self._workspace) / info.destination
        
        if not source_path.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                response_text=f"找不到檔案 {info.source}。"
            )
        
        try:
            source_path.rename(dest_path)
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text=f"已將 {info.source} 重新命名為 {info.destination}。"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"重新命名失敗：{e}"
            )
    
    async def _open_file(self, info: FileOperation) -> CommandResult:
        """Open a file."""
        if not info.source:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請問要開啟哪個檔案？"
            )
        
        filepath = Path(self._workspace) / info.source
        
        if not filepath.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                response_text=f"找不到檔案 {info.source}。"
            )
        
        try:
            if self._system == "Darwin":
                subprocess.run(["open", str(filepath)])
            elif self._system == "Windows":
                os.startfile(str(filepath))
            else:
                subprocess.run(["xdg-open", str(filepath)])
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text=f"已開啟 {info.source}。"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"開啟檔案失敗：{e}"
            )
    
    async def _list_files(self, info: FileOperation) -> CommandResult:
        """List files in directory."""
        dir_path = Path(self._workspace)
        if info.source:
            dir_path = dir_path / info.source
        
        if not dir_path.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                response_text=f"找不到目錄 {info.source or '目前目錄'}。"
            )
        
        try:
            items = list(dir_path.iterdir())
            files = [f.name for f in items if f.is_file()][:10]
            dirs = [f.name for f in items if f.is_dir()][:5]
            
            response_parts = []
            if dirs:
                response_parts.append(f"資料夾：{', '.join(dirs)}")
            if files:
                response_parts.append(f"檔案：{', '.join(files)}")
            
            if not response_parts:
                response_text = "這個目錄是空的。"
            else:
                response_text = "。".join(response_parts)
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data={"files": files, "dirs": dirs},
                response_text=response_text
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"列出檔案失敗：{e}"
            )
    
    async def _copy_file(self, info: FileOperation) -> CommandResult:
        """Copy a file."""
        if not info.source:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請問要複製哪個檔案？"
            )
        
        source_path = Path(self._workspace) / info.source
        
        if not source_path.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                response_text=f"找不到檔案 {info.source}。"
            )
        
        # Generate copy name if no destination
        if not info.destination:
            stem = source_path.stem
            suffix = source_path.suffix
            info.destination = f"{stem}_copy{suffix}"
        
        dest_path = Path(self._workspace) / info.destination
        
        try:
            shutil.copy2(source_path, dest_path)
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text=f"已複製 {info.source} 到 {info.destination}。"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"複製失敗：{e}"
            )
    
    async def _move_file(self, info: FileOperation) -> CommandResult:
        """Move a file."""
        if not info.source or not info.destination:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請提供原位置和目標位置。"
            )
        
        source_path = Path(self._workspace) / info.source
        dest_path = Path(self._workspace) / info.destination
        
        if not source_path.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                response_text=f"找不到 {info.source}。"
            )
        
        try:
            shutil.move(source_path, dest_path)
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text=f"已將 {info.source} 移動到 {info.destination}。"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"移動失敗：{e}"
            )


# ============================================
# Clipboard Operations
# ============================================

class ClipboardHandler(CommandHandler):
    """Handle clipboard voice commands."""
    
    def __init__(self):
        self._system = platform.system()
        self._history: List[str] = []  # Clipboard history
    
    def can_handle(self, intent: Intent) -> bool:
        text = intent.raw_text.lower()
        keywords = ["複製", "copy", "貼上", "paste", "剪貼簿", "clipboard", "剪下", "cut"]
        return any(k in text for k in keywords)
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        text = intent.raw_text.lower()
        
        if "貼上" in text or "paste" in text:
            return await self._paste()
        elif "複製" in text or "copy" in text:
            content = kwargs.get("content") or self._extract_content(intent.raw_text)
            return await self._copy(content)
        elif "清除" in text or "clear" in text:
            return await self._clear()
        elif "歷史" in text or "history" in text:
            return await self._get_history()
        
        return CommandResult(
            status=CommandStatus.FAILED,
            response_text="無法識別剪貼簿操作。"
        )
    
    def _extract_content(self, text: str) -> Optional[str]:
        """Extract content to copy from text."""
        patterns = [
            r"複製\s*[「「]([^」」]+)[」」]",
            r"copy\s*['\"]([^'\"]+)['\"]",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    async def _copy(self, content: Optional[str]) -> CommandResult:
        """Copy content to clipboard."""
        if not content:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請問要複製什麼內容？"
            )
        
        try:
            if self._system == "Darwin":
                process = subprocess.Popen(
                    ["pbcopy"],
                    stdin=subprocess.PIPE
                )
                process.communicate(content.encode("utf-8"))
            elif self._system == "Windows":
                process = subprocess.Popen(
                    ["clip"],
                    stdin=subprocess.PIPE
                )
                process.communicate(content.encode("utf-16"))
            else:
                # Linux - try xclip or xsel
                process = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE
                )
                process.communicate(content.encode("utf-8"))
            
            # Add to history
            self._history.append(content)
            if len(self._history) > 10:
                self._history.pop(0)
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text="已複製到剪貼簿。"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"複製失敗：{e}"
            )
    
    async def _paste(self) -> CommandResult:
        """Get clipboard content."""
        try:
            if self._system == "Darwin":
                result = subprocess.run(
                    ["pbpaste"],
                    capture_output=True,
                    text=True
                )
                content = result.stdout
            elif self._system == "Windows":
                result = subprocess.run(
                    ["powershell", "-command", "Get-Clipboard"],
                    capture_output=True,
                    text=True
                )
                content = result.stdout
            else:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True
                )
                content = result.stdout
            
            if content:
                # Truncate for voice
                display = content[:100] + "..." if len(content) > 100 else content
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    data={"content": content},
                    response_text=f"剪貼簿內容是：{display}"
                )
            else:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    response_text="剪貼簿是空的。"
                )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"讀取剪貼簿失敗：{e}"
            )
    
    async def _clear(self) -> CommandResult:
        """Clear clipboard."""
        try:
            await self._copy("")
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text="已清除剪貼簿。"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e)
            )
    
    async def _get_history(self) -> CommandResult:
        """Get clipboard history."""
        if not self._history:
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text="剪貼簿歷史是空的。"
            )
        
        items = [f"{i+1}. {h[:30]}..." for i, h in enumerate(self._history[-5:])]
        return CommandResult(
            status=CommandStatus.SUCCESS,
            data={"history": self._history},
            response_text=f"最近的剪貼簿內容：{', '.join(items)}"
        )


# ============================================
# Weather Integration
# ============================================

class WeatherHandler(CommandHandler):
    """Handle weather voice queries."""
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("WEATHER_API_KEY")
    
    def can_handle(self, intent: Intent) -> bool:
        text = intent.raw_text.lower()
        keywords = ["天氣", "weather", "氣溫", "temperature", "下雨", "rain", "晴天", "sunny"]
        return any(k in text for k in keywords)
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        text = intent.raw_text
        
        # Extract location
        location = self._extract_location(text)
        
        # Extract time
        is_forecast = any(k in text for k in ["明天", "後天", "週末", "下週", "tomorrow"])
        
        # If no API key, return mock data
        if not self._api_key:
            return await self._mock_weather(location, is_forecast)
        
        return await self._get_weather(location, is_forecast)
    
    def _extract_location(self, text: str) -> str:
        """Extract location from text."""
        # Common Taiwan cities
        cities = [
            "台北", "新北", "桃園", "台中", "台南", "高雄",
            "基隆", "新竹", "嘉義", "屏東", "宜蘭", "花蓮", "台東",
            "Taipei", "Taichung", "Kaohsiung"
        ]
        
        for city in cities:
            if city.lower() in text.lower():
                return city
        
        return "台北"  # Default
    
    async def _mock_weather(self, location: str, is_forecast: bool) -> CommandResult:
        """Return mock weather data."""
        import random
        
        temp = random.randint(18, 32)
        conditions = ["晴天", "多雲", "陰天", "小雨"]
        condition = random.choice(conditions)
        
        if is_forecast:
            response = f"{location}明天預計{condition}，氣溫約{temp}度。建議{'帶傘' if '雨' in condition else '做好防曬'}。"
        else:
            response = f"{location}目前{condition}，氣溫{temp}度。"
        
        return CommandResult(
            status=CommandStatus.SUCCESS,
            data={"location": location, "temp": temp, "condition": condition},
            response_text=response
        )
    
    async def _get_weather(self, location: str, is_forecast: bool) -> CommandResult:
        """Get real weather data from API."""
        import httpx
        
        try:
            # Using OpenWeatherMap API as example
            async with httpx.AsyncClient() as client:
                endpoint = "forecast" if is_forecast else "weather"
                response = await client.get(
                    f"https://api.openweathermap.org/data/2.5/{endpoint}",
                    params={
                        "q": location,
                        "appid": self._api_key,
                        "units": "metric",
                        "lang": "zh_tw"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if is_forecast:
                        # Get tomorrow's forecast
                        tomorrow = data["list"][8] if len(data["list"]) > 8 else data["list"][0]
                        temp = round(tomorrow["main"]["temp"])
                        condition = tomorrow["weather"][0]["description"]
                    else:
                        temp = round(data["main"]["temp"])
                        condition = data["weather"][0]["description"]
                    
                    response_text = f"{location}{'明天' if is_forecast else '目前'}{condition}，氣溫{temp}度。"
                    
                    return CommandResult(
                        status=CommandStatus.SUCCESS,
                        data=data,
                        response_text=response_text
                    )
        except Exception as e:
            logger.error(f"Weather API error: {e}")
        
        # Fallback to mock
        return await self._mock_weather(location, is_forecast)


# ============================================
# Calendar Voice Integration
# ============================================

class CalendarVoiceHandler(CommandHandler):
    """Handle calendar voice commands."""
    
    def can_handle(self, intent: Intent) -> bool:
        return intent.category == IntentCategory.CALENDAR
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        text = intent.raw_text.lower()
        
        # Determine action
        if any(k in text for k in ["查", "有什麼", "行程", "today", "tomorrow"]):
            return await self._query_events(intent)
        elif any(k in text for k in ["新增", "add", "建立", "安排"]):
            return await self._add_event(intent)
        elif any(k in text for k in ["取消", "刪除", "cancel", "delete"]):
            return await self._cancel_event(intent)
        
        return CommandResult(
            status=CommandStatus.FAILED,
            response_text="請告訴我您想查詢、新增還是取消行程？"
        )
    
    async def _query_events(self, intent: Intent) -> CommandResult:
        """Query calendar events."""
        text = intent.raw_text
        
        # Determine date
        if "今天" in text or "today" in text.lower():
            date_str = "今天"
        elif "明天" in text or "tomorrow" in text.lower():
            date_str = "明天"
        elif "這週" in text or "this week" in text.lower():
            date_str = "這週"
        else:
            date_str = "今天"
        
        # Try to get events from Google Calendar
        try:
            from .google_calendar import get_calendar_manager
            
            calendar = get_calendar_manager()
            if calendar:
                events = await calendar.get_events(days=1 if date_str == "今天" else 7)
                
                if events:
                    event_list = []
                    for e in events[:5]:
                        time_str = e.get("start", {}).get("dateTime", "")[:16]
                        summary = e.get("summary", "無標題")
                        event_list.append(f"{time_str} {summary}")
                    
                    return CommandResult(
                        status=CommandStatus.SUCCESS,
                        data={"events": events},
                        response_text=f"{date_str}的行程有：{'、'.join(event_list)}"
                    )
                else:
                    return CommandResult(
                        status=CommandStatus.SUCCESS,
                        response_text=f"{date_str}沒有安排的行程。"
                    )
        except Exception as e:
            logger.debug(f"Calendar query error: {e}")
        
        # Mock response if calendar not available
        return CommandResult(
            status=CommandStatus.SUCCESS,
            response_text=f"{date_str}的行程需要連接 Google 日曆才能查詢。請使用 /google_auth 指令授權。"
        )
    
    async def _add_event(self, intent: Intent) -> CommandResult:
        """Add calendar event."""
        # Extract event details
        text = intent.raw_text
        
        # Extract title
        title_match = re.search(r"(?:安排|新增|add)\s*(.+?)(?:在|於|at|明天|今天|下週|$)", text)
        title = title_match.group(1).strip() if title_match else None
        
        if not title:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請問要新增什麼行程？"
            )
        
        return CommandResult(
            status=CommandStatus.REQUIRES_CONFIRMATION,
            response_text=f"要新增「{title}」到日曆，請問是什麼時間？",
            data={"title": title}
        )
    
    async def _cancel_event(self, intent: Intent) -> CommandResult:
        """Cancel calendar event."""
        return CommandResult(
            status=CommandStatus.REQUIRES_CONFIRMATION,
            response_text="請問要取消哪個行程？"
        )


# ============================================
# Translation Handler
# ============================================

class TranslationHandler(CommandHandler):
    """Handle voice translation requests."""
    
    LANGUAGE_MAP = {
        "中文": "zh-TW",
        "繁體中文": "zh-TW",
        "簡體中文": "zh-CN",
        "英文": "en",
        "english": "en",
        "日文": "ja",
        "japanese": "ja",
        "韓文": "ko",
        "korean": "ko",
        "法文": "fr",
        "french": "fr",
        "德文": "de",
        "german": "de",
        "西班牙文": "es",
        "spanish": "es",
    }
    
    def can_handle(self, intent: Intent) -> bool:
        text = intent.raw_text.lower()
        keywords = ["翻譯", "translate", "怎麼說", "如何說", "意思"]
        return any(k in text for k in keywords)
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        text = intent.raw_text
        
        # Extract text to translate and target language
        content, target_lang = self._parse_translation_request(text)
        
        if not content:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請問要翻譯什麼內容？"
            )
        
        # Perform translation
        return await self._translate(content, target_lang)
    
    def _parse_translation_request(self, text: str) -> Tuple[Optional[str], str]:
        """Parse translation request to extract content and target language."""
        content = None
        target_lang = "en"  # Default to English
        
        # Detect target language
        for lang_name, lang_code in self.LANGUAGE_MAP.items():
            if lang_name in text.lower():
                target_lang = lang_code
                break
        
        # Extract content to translate
        patterns = [
            r"[「「]([^」」]+)[」」]",
            r"翻譯\s*(.+?)(?:成|為|到|$)",
            r"translate\s*(.+?)(?:to|into|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                break
        
        return content, target_lang
    
    async def _translate(self, content: str, target_lang: str) -> CommandResult:
        """Translate content using LLM."""
        try:
            from .llm_providers import get_llm_manager
            
            llm = get_llm_manager()
            
            lang_names = {v: k for k, v in self.LANGUAGE_MAP.items()}
            target_name = lang_names.get(target_lang, target_lang)
            
            prompt = f"請將以下內容翻譯成{target_name}，只回覆翻譯結果：\n\n{content}"
            
            result = await llm.generate(prompt=prompt, max_tokens=200)
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                data={"original": content, "translated": result, "target_lang": target_lang},
                response_text=f"翻譯結果：{result}"
            )
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text="翻譯失敗，請稍後再試。"
            )


# ============================================
# Voice Search Handler
# ============================================

class VoiceSearchHandler(CommandHandler):
    """Handle voice search requests."""
    
    def can_handle(self, intent: Intent) -> bool:
        return intent.category == IntentCategory.SEARCH
    
    async def execute(self, intent: Intent, **kwargs) -> CommandResult:
        text = intent.raw_text.lower()
        
        # Determine search scope
        if any(k in text for k in ["檔案", "file", "文件"]):
            return await self._search_files(intent)
        elif any(k in text for k in ["程式碼", "code", "函數", "function"]):
            return await self._search_code(intent)
        else:
            return await self._search_web(intent)
    
    async def _search_files(self, intent: Intent) -> CommandResult:
        """Search files by name or content."""
        query = self._extract_query(intent.raw_text)
        
        if not query:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請問要搜尋什麼檔案？"
            )
        
        workspace = os.getcwd()
        
        try:
            # Search by filename
            results = []
            for root, dirs, files in os.walk(workspace):
                # Skip common ignored directories
                dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__", ".venv"]]
                
                for file in files:
                    if query.lower() in file.lower():
                        rel_path = os.path.relpath(os.path.join(root, file), workspace)
                        results.append(rel_path)
                        if len(results) >= 10:
                            break
                
                if len(results) >= 10:
                    break
            
            if results:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    data={"files": results},
                    response_text=f"找到 {len(results)} 個相關檔案：{', '.join(results[:5])}"
                )
            else:
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    response_text=f"找不到包含「{query}」的檔案。"
                )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"搜尋失敗：{e}"
            )
    
    async def _search_code(self, intent: Intent) -> CommandResult:
        """Search in code files."""
        query = self._extract_query(intent.raw_text)
        
        if not query:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請問要搜尋什麼程式碼？"
            )
        
        workspace = os.getcwd()
        
        try:
            # Use ripgrep if available
            result = subprocess.run(
                ["rg", "-l", "-i", query, "--max-count=10"],
                cwd=workspace,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout:
                files = result.stdout.strip().split("\n")[:10]
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    data={"files": files, "query": query},
                    response_text=f"找到 {len(files)} 個檔案包含「{query}」：{', '.join(files[:3])}"
                )
        except FileNotFoundError:
            # ripgrep not available, use grep
            pass
        
        return CommandResult(
            status=CommandStatus.SUCCESS,
            response_text=f"找不到包含「{query}」的程式碼。"
        )
    
    async def _search_web(self, intent: Intent) -> CommandResult:
        """Perform web search."""
        query = self._extract_query(intent.raw_text)
        
        if not query:
            return CommandResult(
                status=CommandStatus.REQUIRES_CONFIRMATION,
                response_text="請問要搜尋什麼？"
            )
        
        import urllib.parse
        
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        
        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", url])
            elif platform.system() == "Windows":
                os.startfile(url)
            else:
                subprocess.run(["xdg-open", url])
            
            return CommandResult(
                status=CommandStatus.SUCCESS,
                response_text=f"正在搜尋「{query}」。"
            )
        except Exception as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                error=str(e),
                response_text=f"搜尋失敗：{e}"
            )
    
    def _extract_query(self, text: str) -> Optional[str]:
        """Extract search query from text."""
        patterns = [
            r"搜尋\s*(.+)",
            r"找\s*(.+)",
            r"search\s*(.+)",
            r"查\s*(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                # Remove common suffixes
                query = re.sub(r"(檔案|file|程式碼|code)$", "", query).strip()
                return query if query else None
        
        return None


# ============================================
# Confirmation Handler
# ============================================

class ConfirmationHandler:
    """Handle voice confirmation for dangerous operations."""
    
    def __init__(self):
        self._pending_confirmations: Dict[str, Dict] = {}
    
    def request_confirmation(
        self,
        user_id: str,
        action: str,
        data: Dict[str, Any],
        prompt: str
    ) -> str:
        """Request confirmation for an action."""
        confirmation_id = f"{user_id}_{datetime.now().timestamp()}"
        
        self._pending_confirmations[confirmation_id] = {
            "user_id": user_id,
            "action": action,
            "data": data,
            "prompt": prompt,
            "created_at": datetime.now(),
        }
        
        # Auto-expire after 60 seconds
        asyncio.create_task(self._expire_confirmation(confirmation_id, 60))
        
        return confirmation_id
    
    async def _expire_confirmation(self, confirmation_id: str, seconds: int):
        """Expire a confirmation after timeout."""
        await asyncio.sleep(seconds)
        if confirmation_id in self._pending_confirmations:
            del self._pending_confirmations[confirmation_id]
    
    def check_confirmation(self, text: str, user_id: str) -> Optional[Dict]:
        """Check if text is a confirmation response."""
        text_lower = text.lower()
        
        # Find pending confirmation for user
        for conf_id, conf in list(self._pending_confirmations.items()):
            if conf["user_id"] != user_id:
                continue
            
            # Check for positive confirmation
            if any(p in text_lower for p in ["是", "對", "確定", "好", "yes", "ok", "confirm"]):
                del self._pending_confirmations[conf_id]
                return {"confirmed": True, **conf}
            
            # Check for negative confirmation
            if any(p in text_lower for p in ["不", "否", "取消", "no", "cancel"]):
                del self._pending_confirmations[conf_id]
                return {"confirmed": False, **conf}
        
        return None
    
    def get_pending(self, user_id: str) -> Optional[Dict]:
        """Get pending confirmation for user."""
        for conf_id, conf in self._pending_confirmations.items():
            if conf["user_id"] == user_id:
                return conf
        return None


# ============================================
# Global Instances
# ============================================

_confirmation_handler: Optional[ConfirmationHandler] = None


def get_confirmation_handler() -> ConfirmationHandler:
    """Get or create the global confirmation handler."""
    global _confirmation_handler
    if _confirmation_handler is None:
        _confirmation_handler = ConfirmationHandler()
    return _confirmation_handler


__all__ = [
    # File operations
    "FileOperationType",
    "FileOperation",
    "FileOperationHandler",
    # Clipboard
    "ClipboardHandler",
    # Weather
    "WeatherHandler",
    # Calendar
    "CalendarVoiceHandler",
    # Translation
    "TranslationHandler",
    # Search
    "VoiceSearchHandler",
    # Confirmation
    "ConfirmationHandler",
    "get_confirmation_handler",
]

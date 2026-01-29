"""
Voice Offline Mode for CursorBot v1.1

Provides automatic online/offline mode switching:
- Network connectivity detection
- Automatic fallback to offline engines
- Graceful degradation of features
- Offline intent recognition

Usage:
    from src.core.voice_offline import (
        OfflineModeManager,
        NetworkMonitor,
        OfflineIntentRecognizer,
    )
"""

import asyncio
import socket
import time
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import subprocess
import platform

from ..utils.logger import logger


# ============================================
# Network Monitoring
# ============================================

class NetworkStatus(Enum):
    """Network connectivity status."""
    ONLINE = "online"
    OFFLINE = "offline"
    LIMITED = "limited"  # Has connection but slow/unreliable
    UNKNOWN = "unknown"


@dataclass
class NetworkInfo:
    """Network information."""
    status: NetworkStatus
    latency_ms: Optional[float] = None
    last_check: datetime = field(default_factory=datetime.now)
    connection_type: str = "unknown"  # wifi, ethernet, cellular


class NetworkMonitor:
    """
    Monitors network connectivity.
    
    Features:
    - Periodic connectivity checks
    - Latency measurement
    - Status change callbacks
    """
    
    # Endpoints to check connectivity
    CHECK_ENDPOINTS = [
        ("8.8.8.8", 53),       # Google DNS
        ("1.1.1.1", 53),       # Cloudflare DNS
        ("208.67.222.222", 53),  # OpenDNS
    ]
    
    HTTP_ENDPOINTS = [
        "https://www.google.com",
        "https://api.openai.com",
        "https://www.cloudflare.com",
    ]
    
    def __init__(
        self,
        check_interval: float = 30.0,  # Seconds between checks
        timeout: float = 5.0,
    ):
        self._check_interval = check_interval
        self._timeout = timeout
        self._status = NetworkStatus.UNKNOWN
        self._info = NetworkInfo(status=NetworkStatus.UNKNOWN)
        self._callbacks: List[Callable[[NetworkStatus, NetworkStatus], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start network monitoring."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Network monitor started")
    
    async def stop(self) -> None:
        """Stop network monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Network monitor stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_connectivity()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Network monitor error: {e}")
                await asyncio.sleep(self._check_interval)
    
    async def _check_connectivity(self) -> NetworkInfo:
        """Check network connectivity."""
        old_status = self._status
        
        # Try DNS check first (fastest)
        dns_ok, latency = await self._check_dns()
        
        if dns_ok:
            # Verify with HTTP if DNS works
            http_ok = await self._check_http()
            
            if http_ok:
                self._status = NetworkStatus.ONLINE
            else:
                self._status = NetworkStatus.LIMITED
        else:
            self._status = NetworkStatus.OFFLINE
        
        # Update info
        self._info = NetworkInfo(
            status=self._status,
            latency_ms=latency,
            last_check=datetime.now(),
            connection_type=self._detect_connection_type(),
        )
        
        # Notify if status changed
        if old_status != self._status:
            await self._notify_status_change(old_status, self._status)
        
        return self._info
    
    async def _check_dns(self) -> Tuple[bool, Optional[float]]:
        """Check DNS connectivity."""
        for host, port in self.CHECK_ENDPOINTS:
            try:
                start = time.time()
                
                # Create socket with timeout
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self._timeout)
                
                # Try to connect
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    latency = (time.time() - start) * 1000
                    return True, latency
                    
            except Exception:
                continue
        
        return False, None
    
    async def _check_http(self) -> bool:
        """Check HTTP connectivity."""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                for url in self.HTTP_ENDPOINTS[:1]:  # Just check one
                    try:
                        response = await client.head(url)
                        if response.status_code < 500:
                            return True
                    except Exception:
                        continue
                        
        except ImportError:
            # httpx not available, use basic check
            pass
        
        return False
    
    def _detect_connection_type(self) -> str:
        """Detect the type of network connection."""
        system = platform.system()
        
        try:
            if system == "Darwin":
                # macOS
                result = subprocess.run(
                    ["networksetup", "-getairportnetwork", "en0"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if "Wi-Fi" in result.stdout or "AirPort" in result.stdout:
                    return "wifi"
                
                # Check for ethernet
                result = subprocess.run(
                    ["networksetup", "-getinfo", "Ethernet"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if "IP address" in result.stdout:
                    return "ethernet"
                    
            elif system == "Linux":
                # Linux
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "TYPE", "connection", "show", "--active"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if "wifi" in result.stdout.lower():
                    return "wifi"
                elif "ethernet" in result.stdout.lower():
                    return "ethernet"
                    
        except Exception:
            pass
        
        return "unknown"
    
    async def _notify_status_change(
        self,
        old_status: NetworkStatus,
        new_status: NetworkStatus
    ) -> None:
        """Notify callbacks of status change."""
        logger.info(f"Network status changed: {old_status.value} -> {new_status.value}")
        
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(old_status, new_status)
                else:
                    callback(old_status, new_status)
            except Exception as e:
                logger.error(f"Network callback error: {e}")
    
    def on_status_change(self, callback: Callable) -> None:
        """Register a status change callback."""
        self._callbacks.append(callback)
    
    @property
    def status(self) -> NetworkStatus:
        return self._status
    
    @property
    def info(self) -> NetworkInfo:
        return self._info
    
    @property
    def is_online(self) -> bool:
        return self._status in (NetworkStatus.ONLINE, NetworkStatus.LIMITED)
    
    async def check_now(self) -> NetworkInfo:
        """Force an immediate connectivity check."""
        return await self._check_connectivity()


# ============================================
# Offline Intent Recognition
# ============================================

@dataclass
class OfflineIntent:
    """Offline-recognized intent."""
    name: str
    confidence: float
    slots: Dict[str, str] = field(default_factory=dict)
    raw_text: str = ""


class OfflineIntentRecognizer:
    """
    Local intent recognition without cloud services.
    
    Uses pattern matching and simple NLU.
    """
    
    # Intent patterns (regex-based)
    INTENT_PATTERNS = {
        "open_app": {
            "patterns": [
                r"(?:打開|開啟|執行|啟動|open|launch|run|start)\s*(.+)",
            ],
            "slots": ["app_name"],
        },
        "close_app": {
            "patterns": [
                r"(?:關閉|結束|關掉|close|quit|exit)\s*(.+)",
            ],
            "slots": ["app_name"],
        },
        "search": {
            "patterns": [
                r"(?:搜尋|搜索|查找|找|search|find|look for)\s*(.+)",
            ],
            "slots": ["query"],
        },
        "create_file": {
            "patterns": [
                r"(?:新建|創建|建立|create|new)\s*(?:檔案|文件|file)?\s*(.+)?",
            ],
            "slots": ["filename"],
        },
        "delete_file": {
            "patterns": [
                r"(?:刪除|移除|刪掉|delete|remove)\s*(?:檔案|文件|file)?\s*(.+)?",
            ],
            "slots": ["filename"],
        },
        "play_music": {
            "patterns": [
                r"(?:播放|放|play)\s*(?:音樂|歌|music|song)?\s*(.+)?",
            ],
            "slots": ["song_name"],
        },
        "stop_music": {
            "patterns": [
                r"(?:停止|暫停|stop|pause)\s*(?:音樂|播放|music)?",
            ],
            "slots": [],
        },
        "set_timer": {
            "patterns": [
                r"(?:設定|設置|set)\s*(?:計時器|定時器|timer)\s*(\d+)\s*(?:分鐘|分|秒|minutes?|seconds?)?",
            ],
            "slots": ["duration"],
        },
        "set_reminder": {
            "patterns": [
                r"(?:提醒我|記得|remind me|remember)\s*(.+)",
            ],
            "slots": ["reminder_text"],
        },
        "volume_up": {
            "patterns": [
                r"(?:調高|增加|大聲|volume up|louder)\s*(?:音量)?",
            ],
            "slots": [],
        },
        "volume_down": {
            "patterns": [
                r"(?:調低|降低|小聲|volume down|quieter)\s*(?:音量)?",
            ],
            "slots": [],
        },
        "brightness_up": {
            "patterns": [
                r"(?:調亮|增加|提高)\s*(?:亮度|brightness)",
            ],
            "slots": [],
        },
        "brightness_down": {
            "patterns": [
                r"(?:調暗|降低|減少)\s*(?:亮度|brightness)",
            ],
            "slots": [],
        },
        "weather": {
            "patterns": [
                r"(?:天氣|氣溫|weather)\s*(?:如何|怎麼樣|查詢)?",
                r"(?:今天|明天|今日|明日)\s*(?:天氣|氣溫)",
            ],
            "slots": [],
        },
        "time": {
            "patterns": [
                r"(?:現在|目前)?\s*(?:幾點|時間|what time)",
            ],
            "slots": [],
        },
        "date": {
            "patterns": [
                r"(?:今天|今日)?\s*(?:幾號|日期|什麼日子|what date)",
            ],
            "slots": [],
        },
        "help": {
            "patterns": [
                r"(?:幫助|說明|怎麼|如何|help|how to)",
            ],
            "slots": [],
        },
        "cancel": {
            "patterns": [
                r"^(?:取消|算了|不要了|cancel|never mind)$",
            ],
            "slots": [],
        },
        "yes": {
            "patterns": [
                r"^(?:是|對|好|確認|yes|ok|okay|sure|confirm)$",
            ],
            "slots": [],
        },
        "no": {
            "patterns": [
                r"^(?:否|不|不要|no|nope|cancel)$",
            ],
            "slots": [],
        },
    }
    
    def __init__(self):
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile all regex patterns."""
        for intent, config in self.INTENT_PATTERNS.items():
            self._compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE)
                for p in config["patterns"]
            ]
    
    def recognize(self, text: str) -> Optional[OfflineIntent]:
        """
        Recognize intent from text.
        
        Args:
            text: User input text
            
        Returns:
            OfflineIntent if recognized, None otherwise
        """
        text = text.strip()
        
        best_intent = None
        best_confidence = 0.0
        best_slots = {}
        
        for intent_name, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                
                if match:
                    # Calculate confidence based on match quality
                    matched_len = len(match.group(0))
                    confidence = matched_len / len(text) if text else 0
                    
                    # Boost confidence for full matches
                    if match.group(0).strip() == text.strip():
                        confidence = 1.0
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_intent = intent_name
                        
                        # Extract slots
                        slot_names = self.INTENT_PATTERNS[intent_name].get("slots", [])
                        best_slots = {}
                        
                        for i, slot_name in enumerate(slot_names):
                            group_idx = i + 1
                            if group_idx <= match.lastindex or 0:
                                value = match.group(group_idx)
                                if value:
                                    best_slots[slot_name] = value.strip()
        
        if best_intent and best_confidence > 0.3:
            return OfflineIntent(
                name=best_intent,
                confidence=best_confidence,
                slots=best_slots,
                raw_text=text
            )
        
        return None
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents."""
        return list(self.INTENT_PATTERNS.keys())
    
    def add_pattern(self, intent: str, pattern: str, slots: List[str] = None) -> None:
        """Add a custom pattern for an intent."""
        if intent not in self.INTENT_PATTERNS:
            self.INTENT_PATTERNS[intent] = {"patterns": [], "slots": slots or []}
        
        self.INTENT_PATTERNS[intent]["patterns"].append(pattern)
        
        # Recompile
        if intent not in self._compiled_patterns:
            self._compiled_patterns[intent] = []
        
        self._compiled_patterns[intent].append(
            re.compile(pattern, re.IGNORECASE)
        )


# ============================================
# Offline Mode Manager
# ============================================

@dataclass
class OfflineModeConfig:
    """Offline mode configuration."""
    # Auto-switching
    auto_switch: bool = True
    switch_delay: float = 2.0  # Seconds to wait before switching
    
    # Fallback engines
    stt_offline_engine: str = "vosk"
    tts_offline_engine: str = "piper"
    
    # Feature degradation
    allow_degraded_mode: bool = True
    
    # Caching
    cache_responses: bool = True
    max_cache_size: int = 100


class OfflineModeManager:
    """
    Manages automatic online/offline mode switching.
    
    Features:
    - Automatic mode detection
    - Graceful degradation
    - Engine switching
    - Response caching
    """
    
    def __init__(self, config: OfflineModeConfig = None):
        self.config = config or OfflineModeConfig()
        self._network_monitor = NetworkMonitor()
        self._intent_recognizer = OfflineIntentRecognizer()
        self._is_offline_mode = False
        self._response_cache: Dict[str, str] = {}
        self._mode_callbacks: List[Callable[[bool], None]] = []
        
        # Register network status callback
        self._network_monitor.on_status_change(self._on_network_change)
    
    async def start(self) -> None:
        """Start the offline mode manager."""
        await self._network_monitor.start()
        logger.info("Offline mode manager started")
    
    async def stop(self) -> None:
        """Stop the offline mode manager."""
        await self._network_monitor.stop()
        logger.info("Offline mode manager stopped")
    
    async def _on_network_change(
        self,
        old_status: NetworkStatus,
        new_status: NetworkStatus
    ) -> None:
        """Handle network status changes."""
        if not self.config.auto_switch:
            return
        
        # Add delay before switching to avoid flapping
        await asyncio.sleep(self.config.switch_delay)
        
        # Recheck status
        current_status = self._network_monitor.status
        
        if current_status == NetworkStatus.OFFLINE and not self._is_offline_mode:
            await self._switch_to_offline()
        elif current_status == NetworkStatus.ONLINE and self._is_offline_mode:
            await self._switch_to_online()
    
    async def _switch_to_offline(self) -> None:
        """Switch to offline mode."""
        logger.info("Switching to offline mode")
        self._is_offline_mode = True
        
        # Notify callbacks
        for callback in self._mode_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(True)
                else:
                    callback(True)
            except Exception as e:
                logger.error(f"Mode callback error: {e}")
    
    async def _switch_to_online(self) -> None:
        """Switch to online mode."""
        logger.info("Switching to online mode")
        self._is_offline_mode = False
        
        # Notify callbacks
        for callback in self._mode_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(False)
                else:
                    callback(False)
            except Exception as e:
                logger.error(f"Mode callback error: {e}")
    
    def on_mode_change(self, callback: Callable[[bool], None]) -> None:
        """Register a mode change callback."""
        self._mode_callbacks.append(callback)
    
    @property
    def is_offline(self) -> bool:
        return self._is_offline_mode
    
    @property
    def network_status(self) -> NetworkStatus:
        return self._network_monitor.status
    
    def get_stt_engine(self) -> str:
        """Get appropriate STT engine based on mode."""
        if self._is_offline_mode:
            return self.config.stt_offline_engine
        return "whisper"  # Default online engine
    
    def get_tts_engine(self) -> str:
        """Get appropriate TTS engine based on mode."""
        if self._is_offline_mode:
            return self.config.tts_offline_engine
        return "edge"  # Default online engine
    
    async def process_offline(self, text: str) -> Tuple[Optional[OfflineIntent], str]:
        """
        Process text in offline mode.
        
        Args:
            text: User input
            
        Returns:
            (intent, response)
        """
        # Check cache first
        if self.config.cache_responses and text in self._response_cache:
            return None, self._response_cache[text]
        
        # Try to recognize intent
        intent = self._intent_recognizer.recognize(text)
        
        if intent:
            response = self._generate_offline_response(intent)
        else:
            response = "抱歉，離線模式下無法處理這個請求。請稍後再試，或使用基本指令。"
        
        # Cache response
        if self.config.cache_responses:
            self._cache_response(text, response)
        
        return intent, response
    
    def _generate_offline_response(self, intent: OfflineIntent) -> str:
        """Generate response for offline intent."""
        responses = {
            "time": lambda: f"現在時間是 {datetime.now().strftime('%H:%M')}",
            "date": lambda: f"今天是 {datetime.now().strftime('%Y年%m月%d日')}",
            "help": lambda: "離線模式可用指令：打開應用、搜尋、設定提醒、查詢時間日期",
            "cancel": lambda: "已取消",
            "yes": lambda: "好的，確認",
            "no": lambda: "好的，已取消",
            "volume_up": lambda: "正在調高音量",
            "volume_down": lambda: "正在調低音量",
            "weather": lambda: "離線模式下無法查詢天氣，請連接網路後再試",
        }
        
        if intent.name in responses:
            return responses[intent.name]()
        
        # Default response for actions
        return f"正在執行：{intent.name}"
    
    def _cache_response(self, text: str, response: str) -> None:
        """Cache a response."""
        # Limit cache size
        if len(self._response_cache) >= self.config.max_cache_size:
            # Remove oldest entry
            oldest = next(iter(self._response_cache))
            del self._response_cache[oldest]
        
        self._response_cache[text] = response
    
    def clear_cache(self) -> None:
        """Clear response cache."""
        self._response_cache.clear()
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get available capabilities based on current mode."""
        online_only = {
            "cloud_stt": True,
            "cloud_tts": True,
            "llm_chat": True,
            "web_search": True,
            "translation": True,
            "calendar_sync": True,
            "weather": True,
        }
        
        offline_available = {
            "local_stt": True,
            "local_tts": True,
            "basic_intents": True,
            "system_control": True,
            "file_operations": True,
            "time_date": True,
            "reminders": True,
        }
        
        if self._is_offline_mode:
            return {
                **{k: False for k in online_only},
                **offline_available
            }
        
        return {
            **online_only,
            **offline_available
        }
    
    async def force_offline(self) -> None:
        """Force switch to offline mode."""
        await self._switch_to_offline()
    
    async def force_online(self) -> None:
        """Force switch to online mode (if network available)."""
        if self._network_monitor.is_online:
            await self._switch_to_online()
        else:
            logger.warning("Cannot switch to online mode: no network connection")


# ============================================
# Global Instances
# ============================================

_offline_manager: Optional[OfflineModeManager] = None
_network_monitor: Optional[NetworkMonitor] = None


def get_offline_manager() -> OfflineModeManager:
    global _offline_manager
    if _offline_manager is None:
        _offline_manager = OfflineModeManager()
    return _offline_manager


def get_network_monitor() -> NetworkMonitor:
    global _network_monitor
    if _network_monitor is None:
        _network_monitor = NetworkMonitor()
    return _network_monitor


__all__ = [
    # Network
    "NetworkMonitor",
    "NetworkStatus",
    "NetworkInfo",
    "get_network_monitor",
    # Offline Intent
    "OfflineIntentRecognizer",
    "OfflineIntent",
    # Manager
    "OfflineModeManager",
    "OfflineModeConfig",
    "get_offline_manager",
]

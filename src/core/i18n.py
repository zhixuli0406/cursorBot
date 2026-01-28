"""
Internationalization (i18n) - v0.4 Advanced Feature
Multi-language support for CursorBot.

Supported Languages:
    - zh-TW (Traditional Chinese) - Default
    - zh-CN (Simplified Chinese)
    - en (English)
    - ja (Japanese)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
import json
import os

from ..utils.logger import logger


class Language(Enum):
    """Supported languages."""
    ZH_TW = "zh-TW"  # Traditional Chinese (Default)
    ZH_CN = "zh-CN"  # Simplified Chinese
    EN = "en"        # English
    JA = "ja"        # Japanese


# Default translations
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ============================================
    # Common
    # ============================================
    "welcome": {
        "zh-TW": "歡迎使用 CursorBot！",
        "zh-CN": "欢迎使用 CursorBot！",
        "en": "Welcome to CursorBot!",
        "ja": "CursorBotへようこそ！",
    },
    "error": {
        "zh-TW": "發生錯誤",
        "zh-CN": "发生错误",
        "en": "An error occurred",
        "ja": "エラーが発生しました",
    },
    "success": {
        "zh-TW": "成功",
        "zh-CN": "成功",
        "en": "Success",
        "ja": "成功",
    },
    "failed": {
        "zh-TW": "失敗",
        "zh-CN": "失败",
        "en": "Failed",
        "ja": "失敗",
    },
    "loading": {
        "zh-TW": "載入中...",
        "zh-CN": "加载中...",
        "en": "Loading...",
        "ja": "読み込み中...",
    },
    "processing": {
        "zh-TW": "處理中...",
        "zh-CN": "处理中...",
        "en": "Processing...",
        "ja": "処理中...",
    },
    "done": {
        "zh-TW": "完成",
        "zh-CN": "完成",
        "en": "Done",
        "ja": "完了",
    },
    "cancel": {
        "zh-TW": "取消",
        "zh-CN": "取消",
        "en": "Cancel",
        "ja": "キャンセル",
    },
    "confirm": {
        "zh-TW": "確認",
        "zh-CN": "确认",
        "en": "Confirm",
        "ja": "確認",
    },
    "yes": {
        "zh-TW": "是",
        "zh-CN": "是",
        "en": "Yes",
        "ja": "はい",
    },
    "no": {
        "zh-TW": "否",
        "zh-CN": "否",
        "en": "No",
        "ja": "いいえ",
    },
    
    # ============================================
    # Commands
    # ============================================
    "cmd.help": {
        "zh-TW": "顯示幫助說明",
        "zh-CN": "显示帮助说明",
        "en": "Show help",
        "ja": "ヘルプを表示",
    },
    "cmd.status": {
        "zh-TW": "系統狀態",
        "zh-CN": "系统状态",
        "en": "System status",
        "ja": "システム状態",
    },
    "cmd.new": {
        "zh-TW": "開始新對話",
        "zh-CN": "开始新对话",
        "en": "Start new conversation",
        "ja": "新しい会話を開始",
    },
    "cmd.clear": {
        "zh-TW": "清除對話上下文",
        "zh-CN": "清除对话上下文",
        "en": "Clear conversation context",
        "ja": "会話コンテキストをクリア",
    },
    "cmd.mode": {
        "zh-TW": "切換對話模式",
        "zh-CN": "切换对话模式",
        "en": "Switch conversation mode",
        "ja": "会話モードを切り替え",
    },
    "cmd.model": {
        "zh-TW": "模型設定",
        "zh-CN": "模型设置",
        "en": "Model settings",
        "ja": "モデル設定",
    },
    
    # ============================================
    # Status Messages
    # ============================================
    "status.healthy": {
        "zh-TW": "健康",
        "zh-CN": "健康",
        "en": "Healthy",
        "ja": "正常",
    },
    "status.degraded": {
        "zh-TW": "效能降低",
        "zh-CN": "性能降低",
        "en": "Degraded",
        "ja": "低下",
    },
    "status.unhealthy": {
        "zh-TW": "不健康",
        "zh-CN": "不健康",
        "en": "Unhealthy",
        "ja": "異常",
    },
    "status.online": {
        "zh-TW": "在線",
        "zh-CN": "在线",
        "en": "Online",
        "ja": "オンライン",
    },
    "status.offline": {
        "zh-TW": "離線",
        "zh-CN": "离线",
        "en": "Offline",
        "ja": "オフライン",
    },
    
    # ============================================
    # Error Messages
    # ============================================
    "error.unauthorized": {
        "zh-TW": "未授權存取",
        "zh-CN": "未授权访问",
        "en": "Unauthorized access",
        "ja": "認証されていないアクセス",
    },
    "error.forbidden": {
        "zh-TW": "權限不足",
        "zh-CN": "权限不足",
        "en": "Permission denied",
        "ja": "アクセス権限がありません",
    },
    "error.not_found": {
        "zh-TW": "找不到資源",
        "zh-CN": "找不到资源",
        "en": "Resource not found",
        "ja": "リソースが見つかりません",
    },
    "error.rate_limit": {
        "zh-TW": "請求過於頻繁，請稍後再試",
        "zh-CN": "请求过于频繁，请稍后再试",
        "en": "Too many requests, please try again later",
        "ja": "リクエストが多すぎます。しばらくしてからお試しください",
    },
    "error.timeout": {
        "zh-TW": "操作逾時",
        "zh-CN": "操作超时",
        "en": "Operation timed out",
        "ja": "操作がタイムアウトしました",
    },
    "error.invalid_input": {
        "zh-TW": "輸入無效",
        "zh-CN": "输入无效",
        "en": "Invalid input",
        "ja": "無効な入力",
    },
    "error.elevation_required": {
        "zh-TW": "需要提升權限。請使用 /elevated on",
        "zh-CN": "需要提升权限。请使用 /elevated on",
        "en": "Elevated privileges required. Use /elevated on",
        "ja": "昇格された権限が必要です。/elevated on を使用してください",
    },
    
    # ============================================
    # Features
    # ============================================
    "feature.verbose": {
        "zh-TW": "詳細輸出模式",
        "zh-CN": "详细输出模式",
        "en": "Verbose mode",
        "ja": "詳細出力モード",
    },
    "feature.elevated": {
        "zh-TW": "權限提升模式",
        "zh-CN": "权限提升模式",
        "en": "Elevated mode",
        "ja": "昇格モード",
    },
    "feature.thinking": {
        "zh-TW": "思考模式",
        "zh-CN": "思考模式",
        "en": "Thinking mode",
        "ja": "思考モード",
    },
    "feature.notifications": {
        "zh-TW": "通知設定",
        "zh-CN": "通知设置",
        "en": "Notification settings",
        "ja": "通知設定",
    },
    "feature.alias": {
        "zh-TW": "指令別名",
        "zh-CN": "命令别名",
        "en": "Command aliases",
        "ja": "コマンドエイリアス",
    },
    
    # ============================================
    # Modes
    # ============================================
    "mode.cli": {
        "zh-TW": "CLI 模式",
        "zh-CN": "CLI 模式",
        "en": "CLI mode",
        "ja": "CLIモード",
    },
    "mode.agent": {
        "zh-TW": "Agent 模式",
        "zh-CN": "Agent 模式",
        "en": "Agent mode",
        "ja": "エージェントモード",
    },
    "mode.auto": {
        "zh-TW": "自動模式",
        "zh-CN": "自动模式",
        "en": "Auto mode",
        "ja": "自動モード",
    },
    
    # ============================================
    # Time
    # ============================================
    "time.seconds": {
        "zh-TW": "秒",
        "zh-CN": "秒",
        "en": "seconds",
        "ja": "秒",
    },
    "time.minutes": {
        "zh-TW": "分鐘",
        "zh-CN": "分钟",
        "en": "minutes",
        "ja": "分",
    },
    "time.hours": {
        "zh-TW": "小時",
        "zh-CN": "小时",
        "en": "hours",
        "ja": "時間",
    },
    "time.days": {
        "zh-TW": "天",
        "zh-CN": "天",
        "en": "days",
        "ja": "日",
    },
}


@dataclass
class UserLanguagePreference:
    """User language preference."""
    user_id: str
    language: Language
    auto_detect: bool = True


class I18nManager:
    """
    Internationalization manager.
    
    Usage:
        i18n = get_i18n_manager()
        
        # Set user language
        i18n.set_user_language("user123", Language.EN)
        
        # Get translation
        text = i18n.t("welcome", user_id="user123")
        
        # Get translation with fallback
        text = i18n.t("unknown.key", default="Fallback text")
        
        # Format with variables
        text = i18n.t("greeting", name="John")  # "Hello, {name}!"
    """
    
    _instance: Optional["I18nManager"] = None
    
    def __init__(self):
        self._translations = TRANSLATIONS.copy()
        self._user_languages: Dict[str, UserLanguagePreference] = {}
        self._default_language = Language.ZH_TW
        self._data_path = "data/i18n_preferences.json"
        self._custom_translations_path = "data/i18n"
        self._load_preferences()
        self._load_custom_translations()
    
    def _load_preferences(self):
        """Load user language preferences."""
        try:
            if os.path.exists(self._data_path):
                with open(self._data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, pref_data in data.items():
                        self._user_languages[user_id] = UserLanguagePreference(
                            user_id=user_id,
                            language=Language(pref_data.get("language", "zh-TW")),
                            auto_detect=pref_data.get("auto_detect", True),
                        )
        except Exception as e:
            logger.warning(f"Failed to load i18n preferences: {e}")
    
    def _save_preferences(self):
        """Save user language preferences."""
        try:
            os.makedirs(os.path.dirname(self._data_path), exist_ok=True)
            data = {
                user_id: {
                    "language": pref.language.value,
                    "auto_detect": pref.auto_detect,
                }
                for user_id, pref in self._user_languages.items()
            }
            with open(self._data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save i18n preferences: {e}")
    
    def _load_custom_translations(self):
        """Load custom translations from files."""
        try:
            if os.path.exists(self._custom_translations_path):
                for filename in os.listdir(self._custom_translations_path):
                    if filename.endswith(".json"):
                        lang_code = filename[:-5]  # Remove .json
                        filepath = os.path.join(self._custom_translations_path, filename)
                        with open(filepath, "r", encoding="utf-8") as f:
                            custom = json.load(f)
                            for key, value in custom.items():
                                if key not in self._translations:
                                    self._translations[key] = {}
                                self._translations[key][lang_code] = value
        except Exception as e:
            logger.warning(f"Failed to load custom translations: {e}")
    
    def set_default_language(self, language: Language):
        """Set the default language."""
        self._default_language = language
    
    def get_user_language(self, user_id: str) -> Language:
        """Get language preference for a user."""
        pref = self._user_languages.get(user_id)
        return pref.language if pref else self._default_language
    
    def set_user_language(self, user_id: str, language: Language):
        """Set language preference for a user."""
        self._user_languages[user_id] = UserLanguagePreference(
            user_id=user_id,
            language=language,
        )
        self._save_preferences()
        logger.info(f"Set language for user {user_id}: {language.value}")
    
    def t(
        self,
        key: str,
        user_id: str = None,
        language: Language = None,
        default: str = None,
        **kwargs,
    ) -> str:
        """
        Get translation for a key.
        
        Args:
            key: Translation key (e.g., "welcome", "error.unauthorized")
            user_id: User ID to get language preference
            language: Override language
            default: Default text if translation not found
            **kwargs: Variables for string formatting
            
        Returns:
            Translated string
        """
        # Determine language
        if language is None:
            if user_id:
                language = self.get_user_language(user_id)
            else:
                language = self._default_language
        
        lang_code = language.value
        
        # Get translation
        translations = self._translations.get(key, {})
        
        # Try exact language match
        text = translations.get(lang_code)
        
        # Try language without region (e.g., "zh" for "zh-TW")
        if text is None and "-" in lang_code:
            base_lang = lang_code.split("-")[0]
            text = translations.get(base_lang)
        
        # Try default language
        if text is None:
            text = translations.get(self._default_language.value)
        
        # Use key or default as fallback
        if text is None:
            text = default or key
        
        # Format with variables
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        
        return text
    
    def add_translation(self, key: str, language: Language, text: str):
        """Add or update a translation."""
        if key not in self._translations:
            self._translations[key] = {}
        self._translations[key][language.value] = text
    
    def get_available_languages(self) -> List[Language]:
        """Get list of available languages."""
        return list(Language)
    
    def get_language_name(self, language: Language) -> str:
        """Get display name for a language."""
        names = {
            Language.ZH_TW: "繁體中文",
            Language.ZH_CN: "简体中文",
            Language.EN: "English",
            Language.JA: "日本語",
        }
        return names.get(language, language.value)
    
    def detect_language(self, text: str) -> Language:
        """
        Detect language from text.
        
        Simple heuristic detection.
        """
        # Check for CJK characters
        has_cjk = any('\u4e00' <= char <= '\u9fff' for char in text)
        has_japanese = any('\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff' for char in text)
        
        if has_japanese:
            return Language.JA
        elif has_cjk:
            # Check for simplified Chinese specific characters
            simplified_chars = set('个么这那着过给说对会时为从')
            if any(char in simplified_chars for char in text):
                return Language.ZH_CN
            return Language.ZH_TW
        else:
            return Language.EN
    
    def get_status_message(self, user_id: str) -> str:
        """Get formatted status message."""
        current = self.get_user_language(user_id)
        
        lines = [
            "🌐 **" + self.t("feature.language", user_id=user_id, default="Language Settings") + "**",
            "",
            f"Current: **{self.get_language_name(current)}** ({current.value})",
            "",
            "**Available Languages:**",
        ]
        
        for lang in Language:
            marker = "✓" if lang == current else " "
            lines.append(f"{marker} {self.get_language_name(lang)} ({lang.value})")
        
        lines.extend([
            "",
            "**Commands:**",
            "/lang <code> - Set language",
            "/lang auto - Auto-detect",
        ])
        
        return "\n".join(lines)


# Singleton instance
_i18n_manager: Optional[I18nManager] = None


def get_i18n_manager() -> I18nManager:
    """Get the global i18n manager instance."""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager


def reset_i18n_manager():
    """Reset the manager (for testing)."""
    global _i18n_manager
    _i18n_manager = None


def t(key: str, user_id: str = None, **kwargs) -> str:
    """Shortcut function for translation."""
    return get_i18n_manager().t(key, user_id=user_id, **kwargs)


__all__ = [
    "Language",
    "TRANSLATIONS",
    "UserLanguagePreference",
    "I18nManager",
    "get_i18n_manager",
    "reset_i18n_manager",
    "t",
]

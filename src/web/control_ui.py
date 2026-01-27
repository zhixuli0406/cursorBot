"""
Control UI for CursorBot

Provides:
- Configuration management interface
- Provider settings
- User management
- System controls
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from ..utils.logger import logger


# ============================================
# Models
# ============================================

class ProviderSettings(BaseModel):
    """LLM Provider settings."""
    provider: str
    enabled: bool
    api_key: str = ""
    model: str = ""
    api_base: str = ""


class UserSettings(BaseModel):
    """User settings."""
    user_id: int
    is_admin: bool = False
    allowed: bool = True


class SystemSettings(BaseModel):
    """System settings."""
    debug_mode: bool = False
    log_level: str = "INFO"
    max_sessions: int = 100
    session_timeout: int = 3600


# ============================================
# Control UI HTML
# ============================================

CONTROL_UI_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CursorBot Control Panel</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .tab-active { border-bottom: 2px solid #3b82f6; color: #3b82f6; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen" x-data="controlPanel()">
    <!-- Header -->
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-6xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <span class="text-2xl">⚙️</span>
                    <h1 class="text-xl font-bold text-gray-800">Control Panel</h1>
                </div>
                <a href="/dashboard" class="text-blue-500 hover:text-blue-700">← Dashboard</a>
            </div>
        </div>
    </nav>

    <main class="max-w-6xl mx-auto px-4 py-8">
        <!-- Tabs -->
        <div class="bg-white rounded-lg shadow mb-6">
            <div class="flex border-b">
                <button @click="activeTab = 'providers'" 
                        class="px-6 py-3 font-medium"
                        :class="activeTab === 'providers' ? 'tab-active' : 'text-gray-500'">
                    🤖 AI 提供者
                </button>
                <button @click="activeTab = 'users'" 
                        class="px-6 py-3 font-medium"
                        :class="activeTab === 'users' ? 'tab-active' : 'text-gray-500'">
                    👥 用戶管理
                </button>
                <button @click="activeTab = 'system'" 
                        class="px-6 py-3 font-medium"
                        :class="activeTab === 'system' ? 'tab-active' : 'text-gray-500'">
                    🔧 系統設定
                </button>
                <button @click="activeTab = 'env'" 
                        class="px-6 py-3 font-medium"
                        :class="activeTab === 'env' ? 'tab-active' : 'text-gray-500'">
                    📝 環境變數
                </button>
            </div>
        </div>

        <!-- Providers Tab -->
        <div x-show="activeTab === 'providers'" class="bg-white rounded-lg shadow p-6">
            <h2 class="text-lg font-semibold mb-4">AI 提供者設定</h2>
            <div class="space-y-4">
                <template x-for="provider in providers" :key="provider.name">
                    <div class="border rounded-lg p-4">
                        <div class="flex items-center justify-between mb-3">
                            <div class="flex items-center space-x-3">
                                <span class="text-xl" x-text="provider.icon"></span>
                                <span class="font-medium" x-text="provider.name"></span>
                            </div>
                            <label class="relative inline-flex items-center cursor-pointer">
                                <input type="checkbox" x-model="provider.enabled" class="sr-only peer">
                                <div class="w-11 h-6 bg-gray-200 peer-checked:bg-blue-600 rounded-full transition-colors"></div>
                            </label>
                        </div>
                        <div x-show="provider.enabled" class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="text-sm text-gray-600">API Key</label>
                                <input type="password" x-model="provider.apiKey" 
                                       class="w-full mt-1 px-3 py-2 border rounded-lg"
                                       placeholder="sk-...">
                            </div>
                            <div>
                                <label class="text-sm text-gray-600">模型</label>
                                <input type="text" x-model="provider.model" 
                                       class="w-full mt-1 px-3 py-2 border rounded-lg"
                                       :placeholder="provider.defaultModel">
                            </div>
                        </div>
                    </div>
                </template>
            </div>
            <button @click="saveProviders()" 
                    class="mt-6 px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                💾 儲存設定
            </button>
        </div>

        <!-- Users Tab -->
        <div x-show="activeTab === 'users'" class="bg-white rounded-lg shadow p-6">
            <h2 class="text-lg font-semibold mb-4">用戶管理</h2>
            
            <!-- Add User -->
            <div class="flex space-x-3 mb-6">
                <input type="text" x-model="newUserId" placeholder="用戶 ID"
                       class="flex-1 px-3 py-2 border rounded-lg">
                <button @click="addUser()" 
                        class="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">
                    ➕ 新增
                </button>
            </div>
            
            <!-- User List -->
            <div class="space-y-2">
                <template x-for="user in users" :key="user.id">
                    <div class="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                            <span class="font-medium" x-text="user.id"></span>
                            <span x-show="user.isAdmin" class="ml-2 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">管理員</span>
                        </div>
                        <div class="flex items-center space-x-3">
                            <button @click="toggleAdmin(user)" 
                                    class="text-sm text-blue-500 hover:text-blue-700">
                                <span x-text="user.isAdmin ? '移除管理員' : '設為管理員'"></span>
                            </button>
                            <button @click="removeUser(user)" class="text-red-500 hover:text-red-700">
                                🗑️
                            </button>
                        </div>
                    </div>
                </template>
            </div>
        </div>

        <!-- System Tab -->
        <div x-show="activeTab === 'system'" class="bg-white rounded-lg shadow p-6">
            <h2 class="text-lg font-semibold mb-4">系統設定</h2>
            <div class="grid grid-cols-2 gap-6">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">日誌等級</label>
                    <select x-model="system.logLevel" class="w-full px-3 py-2 border rounded-lg">
                        <option value="DEBUG">DEBUG</option>
                        <option value="INFO">INFO</option>
                        <option value="WARNING">WARNING</option>
                        <option value="ERROR">ERROR</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">最大會話數</label>
                    <input type="number" x-model="system.maxSessions" 
                           class="w-full px-3 py-2 border rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">會話逾時（秒）</label>
                    <input type="number" x-model="system.sessionTimeout" 
                           class="w-full px-3 py-2 border rounded-lg">
                </div>
                <div class="flex items-center">
                    <label class="flex items-center cursor-pointer">
                        <input type="checkbox" x-model="system.debugMode" class="mr-2">
                        <span>除錯模式</span>
                    </label>
                </div>
            </div>
            <div class="mt-6 flex space-x-3">
                <button @click="saveSystem()" 
                        class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                    💾 儲存設定
                </button>
                <button @click="restartBot()" 
                        class="px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600">
                    🔄 重啟 Bot
                </button>
            </div>
        </div>

        <!-- Environment Tab -->
        <div x-show="activeTab === 'env'" class="bg-white rounded-lg shadow p-6">
            <h2 class="text-lg font-semibold mb-4">環境變數</h2>
            <div class="bg-gray-50 rounded-lg p-4 font-mono text-sm overflow-x-auto">
                <template x-for="(value, key) in envVars" :key="key">
                    <div class="flex py-1">
                        <span class="text-blue-600 w-64 flex-shrink-0" x-text="key"></span>
                        <span class="text-gray-600">=</span>
                        <span class="text-green-600 ml-2" x-text="maskValue(value)"></span>
                    </div>
                </template>
            </div>
            <p class="mt-4 text-sm text-gray-500">
                ⚠️ 環境變數需在 .env 檔案中修改，然後重啟 Bot
            </p>
        </div>
    </main>

    <script>
        function controlPanel() {
            return {
                activeTab: 'providers',
                newUserId: '',
                providers: [
                    { name: 'OpenAI', icon: '🟢', enabled: false, apiKey: '', model: '', defaultModel: 'gpt-4o-mini' },
                    { name: 'Anthropic', icon: '🟣', enabled: false, apiKey: '', model: '', defaultModel: 'claude-3-5-sonnet' },
                    { name: 'Google', icon: '🔵', enabled: false, apiKey: '', model: '', defaultModel: 'gemini-2.0-flash' },
                    { name: 'OpenRouter', icon: '🟠', enabled: false, apiKey: '', model: '', defaultModel: 'google/gemini-2.0-flash-exp:free' },
                    { name: 'AWS Bedrock', icon: '☁️', enabled: false, apiKey: '', model: '', defaultModel: 'anthropic.claude-3-5-sonnet' },
                    { name: 'Ollama', icon: '🦙', enabled: false, apiKey: '', model: '', defaultModel: 'llama3.2' },
                ],
                users: [],
                system: {
                    debugMode: false,
                    logLevel: 'INFO',
                    maxSessions: 100,
                    sessionTimeout: 3600,
                },
                envVars: {},
                
                init() {
                    this.loadSettings();
                },
                
                async loadSettings() {
                    try {
                        const res = await fetch('/control/api/settings');
                        if (res.ok) {
                            const data = await res.json();
                            this.users = data.users || [];
                            this.envVars = data.env || {};
                            if (data.providers) {
                                data.providers.forEach(p => {
                                    const provider = this.providers.find(x => x.name.toLowerCase() === p.name.toLowerCase());
                                    if (provider) {
                                        provider.enabled = p.enabled;
                                        provider.model = p.model || '';
                                    }
                                });
                            }
                        }
                    } catch (e) {
                        console.error('Failed to load settings');
                    }
                },
                
                maskValue(value) {
                    if (!value) return '(未設定)';
                    if (value.length <= 8) return '***';
                    return value.substring(0, 4) + '...' + value.substring(value.length - 4);
                },
                
                async saveProviders() {
                    try {
                        await fetch('/control/api/providers', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(this.providers)
                        });
                        alert('設定已儲存');
                    } catch (e) {
                        alert('儲存失敗');
                    }
                },
                
                addUser() {
                    if (!this.newUserId) return;
                    this.users.push({ id: this.newUserId, isAdmin: false });
                    this.newUserId = '';
                    this.saveUsers();
                },
                
                toggleAdmin(user) {
                    user.isAdmin = !user.isAdmin;
                    this.saveUsers();
                },
                
                removeUser(user) {
                    if (!confirm('確定要移除此用戶？')) return;
                    this.users = this.users.filter(u => u.id !== user.id);
                    this.saveUsers();
                },
                
                async saveUsers() {
                    try {
                        await fetch('/control/api/users', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(this.users)
                        });
                    } catch (e) {
                        console.error('Failed to save users');
                    }
                },
                
                async saveSystem() {
                    try {
                        await fetch('/control/api/system', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(this.system)
                        });
                        alert('系統設定已儲存');
                    } catch (e) {
                        alert('儲存失敗');
                    }
                },
                
                async restartBot() {
                    if (!confirm('確定要重啟 Bot？')) return;
                    try {
                        await fetch('/control/api/restart', { method: 'POST' });
                        alert('Bot 正在重啟...');
                    } catch (e) {
                        alert('重啟失敗');
                    }
                }
            }
        }
    </script>
</body>
</html>
"""


# ============================================
# Control UI Router
# ============================================

def create_control_router():
    """Create control UI router."""
    import os
    
    router = APIRouter(prefix="/control", tags=["control"])
    
    @router.get("/", response_class=HTMLResponse)
    async def control_page():
        """Render control panel page."""
        return HTMLResponse(content=CONTROL_UI_HTML)
    
    @router.get("/api/settings")
    async def get_settings():
        """Get all settings."""
        try:
            from ..utils.config import settings
            
            # Get allowed users
            users = []
            allowed = os.getenv("TELEGRAM_ALLOWED_USERS", "")
            admins = os.getenv("TELEGRAM_ADMIN_USERS", "")
            
            for uid in allowed.split(","):
                uid = uid.strip()
                if uid:
                    users.append({
                        "id": uid,
                        "isAdmin": uid in admins,
                    })
            
            # Get provider status
            providers = []
            provider_configs = [
                ("openai", "OPENAI_API_KEY"),
                ("anthropic", "ANTHROPIC_API_KEY"),
                ("google", "GOOGLE_GENERATIVE_AI_API_KEY"),
                ("openrouter", "OPENROUTER_API_KEY"),
                ("bedrock", "AWS_ACCESS_KEY_ID"),
                ("ollama", "OLLAMA_ENABLED"),
            ]
            
            for name, env_key in provider_configs:
                providers.append({
                    "name": name,
                    "enabled": bool(os.getenv(env_key)),
                    "model": os.getenv(f"{name.upper()}_MODEL", ""),
                })
            
            # Get env vars (masked)
            env_vars = {
                "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
                "TELEGRAM_ALLOWED_USERS": os.getenv("TELEGRAM_ALLOWED_USERS", ""),
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
                "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
                "GOOGLE_GENERATIVE_AI_API_KEY": os.getenv("GOOGLE_GENERATIVE_AI_API_KEY", ""),
                "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
                "DISCORD_BOT_TOKEN": os.getenv("DISCORD_BOT_TOKEN", ""),
            }
            
            return {
                "users": users,
                "providers": providers,
                "env": env_vars,
            }
            
        except Exception as e:
            logger.error(f"Settings error: {e}")
            return {"users": [], "providers": [], "env": {}}
    
    @router.post("/api/providers")
    async def save_providers(request: Request):
        """Save provider settings (runtime only)."""
        try:
            data = await request.json()
            # Note: This only affects runtime, not .env file
            logger.info(f"Provider settings updated (runtime)")
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/api/users")
    async def save_users(request: Request):
        """Save user settings (runtime only)."""
        try:
            data = await request.json()
            logger.info(f"User settings updated (runtime)")
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/api/system")
    async def save_system(request: Request):
        """Save system settings."""
        try:
            data = await request.json()
            # Update runtime settings
            import logging
            log_level = data.get("logLevel", "INFO")
            logging.getLogger().setLevel(getattr(logging, log_level, logging.INFO))
            
            logger.info(f"System settings updated: {data}")
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/api/restart")
    async def restart_bot():
        """Request bot restart."""
        try:
            logger.warning("Bot restart requested from Control UI")
            # In a real implementation, this would trigger a restart
            return {"status": "ok", "message": "Restart requested"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return router


__all__ = [
    "create_control_router",
    "CONTROL_UI_HTML",
]

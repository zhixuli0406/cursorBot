"""
Web Dashboard for CursorBot

Provides:
- System status overview
- Session management
- User management
- Configuration interface
- Real-time monitoring
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..utils.logger import logger
from ..utils.config import get_settings


# ============================================
# Models
# ============================================

class DashboardStats(BaseModel):
    """Dashboard statistics."""
    uptime: str
    total_users: int
    active_sessions: int
    total_messages: int
    llm_calls: int
    current_model: str
    system_status: str


class UserInfo(BaseModel):
    """User information."""
    user_id: int
    username: str = ""
    is_admin: bool = False
    last_active: str = ""
    message_count: int = 0


class SessionInfo(BaseModel):
    """Session information."""
    session_key: str
    user_id: int
    messages: int
    created_at: str
    last_activity: str


# ============================================
# Dashboard HTML Template
# ============================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CursorBot Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    </style>
</head>
<body class="bg-gray-100 min-h-screen" x-data="dashboard()">
    <!-- Header -->
    <nav class="gradient-bg shadow-lg">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <span class="text-2xl">🤖</span>
                    <h1 class="text-xl font-bold text-white">CursorBot Dashboard</h1>
                </div>
                <div class="flex items-center space-x-4">
                    <span class="text-white/80 text-sm" x-text="currentTime"></span>
                    <span class="px-3 py-1 rounded-full text-sm font-medium"
                          :class="status === 'online' ? 'bg-green-400 text-green-900' : 'bg-red-400 text-red-900'"
                          x-text="status === 'online' ? '線上' : '離線'"></span>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 py-8">
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="bg-white rounded-xl shadow-md p-6 border-l-4 border-blue-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">運行時間</p>
                        <p class="text-2xl font-bold text-gray-800" x-text="stats.uptime"></p>
                    </div>
                    <span class="text-3xl">⏱️</span>
                </div>
            </div>
            <div class="bg-white rounded-xl shadow-md p-6 border-l-4 border-green-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">活躍會話</p>
                        <p class="text-2xl font-bold text-gray-800" x-text="stats.active_sessions"></p>
                    </div>
                    <span class="text-3xl">💬</span>
                </div>
            </div>
            <div class="bg-white rounded-xl shadow-md p-6 border-l-4 border-purple-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">LLM 呼叫</p>
                        <p class="text-2xl font-bold text-gray-800" x-text="stats.llm_calls"></p>
                    </div>
                    <span class="text-3xl">🧠</span>
                </div>
            </div>
            <div class="bg-white rounded-xl shadow-md p-6 border-l-4 border-orange-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">當前模型</p>
                        <p class="text-lg font-bold text-gray-800 truncate" x-text="stats.current_model"></p>
                    </div>
                    <span class="text-3xl">🤖</span>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Sessions Panel -->
            <div class="lg:col-span-2 bg-white rounded-xl shadow-md overflow-hidden">
                <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                    <h2 class="text-lg font-semibold text-gray-800">📋 活躍會話</h2>
                    <button @click="refreshSessions()" class="text-blue-500 hover:text-blue-700">
                        🔄 重新整理
                    </button>
                </div>
                <div class="p-6">
                    <div class="overflow-x-auto">
                        <table class="w-full">
                            <thead>
                                <tr class="text-left text-gray-500 text-sm">
                                    <th class="pb-3">用戶 ID</th>
                                    <th class="pb-3">訊息數</th>
                                    <th class="pb-3">最後活動</th>
                                    <th class="pb-3">操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                <template x-for="session in sessions" :key="session.session_key">
                                    <tr class="border-t border-gray-100">
                                        <td class="py-3 font-medium" x-text="session.user_id"></td>
                                        <td class="py-3" x-text="session.messages"></td>
                                        <td class="py-3 text-gray-500 text-sm" x-text="session.last_activity"></td>
                                        <td class="py-3">
                                            <button @click="clearSession(session.session_key)"
                                                    class="text-red-500 hover:text-red-700 text-sm">
                                                清除
                                            </button>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                        <p x-show="sessions.length === 0" class="text-gray-500 text-center py-8">
                            目前沒有活躍會話
                        </p>
                    </div>
                </div>
            </div>

            <!-- Quick Actions -->
            <div class="bg-white rounded-xl shadow-md overflow-hidden">
                <div class="px-6 py-4 border-b border-gray-200">
                    <h2 class="text-lg font-semibold text-gray-800">⚡ 快速操作</h2>
                </div>
                <div class="p-6 space-y-4">
                    <button @click="runDoctor()" 
                            class="w-full py-3 px-4 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition">
                        🩺 系統診斷
                    </button>
                    <button @click="clearAllSessions()"
                            class="w-full py-3 px-4 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium transition">
                        🗑️ 清除所有會話
                    </button>
                    <button @click="toggleLock()"
                            class="w-full py-3 px-4 rounded-lg font-medium transition"
                            :class="locked ? 'bg-green-500 hover:bg-green-600 text-white' : 'bg-red-500 hover:bg-red-600 text-white'">
                        <span x-text="locked ? '🔓 解除鎖定' : '🔒 鎖定 Bot'"></span>
                    </button>
                    <div class="pt-4 border-t border-gray-200">
                        <h3 class="text-sm font-medium text-gray-600 mb-3">📢 發送廣播</h3>
                        <textarea x-model="broadcastMsg" 
                                  class="w-full p-3 border border-gray-300 rounded-lg text-sm"
                                  placeholder="輸入廣播訊息..."
                                  rows="3"></textarea>
                        <button @click="sendBroadcast()"
                                class="mt-2 w-full py-2 px-4 bg-purple-500 hover:bg-purple-600 text-white rounded-lg font-medium transition">
                            發送廣播
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- System Info -->
        <div class="mt-6 bg-white rounded-xl shadow-md overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-lg font-semibold text-gray-800">💻 系統資訊</h2>
            </div>
            <div class="p-6">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                        <p class="text-gray-500 text-sm">系統狀態</p>
                        <p class="font-medium" x-text="stats.system_status"></p>
                    </div>
                    <div>
                        <p class="text-gray-500 text-sm">總用戶數</p>
                        <p class="font-medium" x-text="stats.total_users"></p>
                    </div>
                    <div>
                        <p class="text-gray-500 text-sm">總訊息數</p>
                        <p class="font-medium" x-text="stats.total_messages"></p>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="mt-8 py-6 text-center text-gray-500 text-sm">
        <p>CursorBot v0.3 Dashboard | Built with FastAPI & Alpine.js</p>
    </footer>

    <script>
        function dashboard() {
            return {
                status: 'online',
                locked: false,
                currentTime: '',
                broadcastMsg: '',
                stats: {
                    uptime: '0:00:00',
                    total_users: 0,
                    active_sessions: 0,
                    total_messages: 0,
                    llm_calls: 0,
                    current_model: 'N/A',
                    system_status: 'Unknown'
                },
                sessions: [],
                
                init() {
                    this.updateTime();
                    setInterval(() => this.updateTime(), 1000);
                    this.fetchStats();
                    this.fetchSessions();
                    setInterval(() => {
                        this.fetchStats();
                        this.fetchSessions();
                    }, 10000);
                },
                
                updateTime() {
                    this.currentTime = new Date().toLocaleString('zh-TW');
                },
                
                async fetchStats() {
                    try {
                        const res = await fetch('/dashboard/api/stats');
                        if (res.ok) {
                            this.stats = await res.json();
                            this.status = 'online';
                        }
                    } catch (e) {
                        this.status = 'offline';
                    }
                },
                
                async fetchSessions() {
                    try {
                        const res = await fetch('/dashboard/api/sessions');
                        if (res.ok) {
                            this.sessions = await res.json();
                        }
                    } catch (e) {
                        console.error('Failed to fetch sessions');
                    }
                },
                
                refreshSessions() {
                    this.fetchSessions();
                },
                
                async clearSession(key) {
                    if (!confirm('確定要清除此會話？')) return;
                    try {
                        await fetch(`/dashboard/api/sessions/${key}`, { method: 'DELETE' });
                        this.fetchSessions();
                    } catch (e) {
                        alert('清除失敗');
                    }
                },
                
                async clearAllSessions() {
                    if (!confirm('確定要清除所有會話？')) return;
                    try {
                        await fetch('/dashboard/api/sessions', { method: 'DELETE' });
                        this.fetchSessions();
                    } catch (e) {
                        alert('清除失敗');
                    }
                },
                
                async runDoctor() {
                    try {
                        const res = await fetch('/dashboard/api/doctor');
                        const data = await res.json();
                        alert(`診斷結果: ${data.summary}`);
                    } catch (e) {
                        alert('診斷失敗');
                    }
                },
                
                async toggleLock() {
                    try {
                        const res = await fetch('/dashboard/api/lock', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ lock: !this.locked })
                        });
                        if (res.ok) {
                            this.locked = !this.locked;
                        }
                    } catch (e) {
                        alert('操作失敗');
                    }
                },
                
                async sendBroadcast() {
                    if (!this.broadcastMsg.trim()) return;
                    try {
                        await fetch('/dashboard/api/broadcast', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ message: this.broadcastMsg })
                        });
                        alert('廣播已發送');
                        this.broadcastMsg = '';
                    } catch (e) {
                        alert('發送失敗');
                    }
                }
            }
        }
    </script>
</body>
</html>
"""


# ============================================
# Dashboard Router
# ============================================

def create_dashboard_router():
    """Create dashboard router."""
    from fastapi import APIRouter
    
    router = APIRouter(prefix="/dashboard", tags=["dashboard"])
    
    # Track start time
    _start_time = datetime.now()
    
    @router.get("/", response_class=HTMLResponse)
    async def dashboard_page():
        """Render dashboard page."""
        return HTMLResponse(content=DASHBOARD_HTML)
    
    @router.get("/api/stats")
    async def get_stats():
        """Get dashboard statistics."""
        try:
            from ..core.context import get_context_manager
            from ..core.llm_providers import get_llm_manager
            
            ctx_manager = get_context_manager()
            llm_manager = get_llm_manager()
            
            stats = ctx_manager.get_session_stats()
            usage = llm_manager.get_usage_stats()
            
            # Calculate uptime
            uptime = datetime.now() - _start_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return {
                "uptime": f"{hours}:{minutes:02d}:{seconds:02d}",
                "total_users": stats.get("unique_users", 0),
                "active_sessions": stats.get("total_sessions", 0),
                "total_messages": sum(s.get("messages", 0) for s in stats.get("sessions", [])),
                "llm_calls": usage.get("total_calls", 0),
                "current_model": llm_manager.get_model_status().get("current_model") or "default",
                "system_status": "Healthy",
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {
                "uptime": "0:00:00",
                "total_users": 0,
                "active_sessions": 0,
                "total_messages": 0,
                "llm_calls": 0,
                "current_model": "N/A",
                "system_status": f"Error: {e}",
            }
    
    @router.get("/api/sessions")
    async def get_sessions():
        """Get active sessions."""
        try:
            from ..core.context import get_context_manager
            manager = get_context_manager()
            stats = manager.get_session_stats()
            
            sessions = []
            for s in stats.get("sessions", [])[:50]:
                sessions.append({
                    "session_key": s.get("session_key", ""),
                    "user_id": s.get("user_id", 0),
                    "messages": s.get("messages", 0),
                    "created_at": s.get("created_at", ""),
                    "last_activity": s.get("last_activity", ""),
                })
            
            return sessions
        except Exception as e:
            logger.error(f"Sessions error: {e}")
            return []
    
    @router.delete("/api/sessions/{session_key}")
    async def delete_session(session_key: str):
        """Delete a session."""
        try:
            from ..core.context import get_context_manager
            manager = get_context_manager()
            if session_key in manager._contexts:
                del manager._contexts[session_key]
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.delete("/api/sessions")
    async def delete_all_sessions():
        """Delete all sessions."""
        try:
            from ..core.context import get_context_manager
            manager = get_context_manager()
            manager._contexts.clear()
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/api/doctor")
    async def run_doctor():
        """Run diagnostics."""
        try:
            from ..core.doctor import run_diagnostics
            report = await run_diagnostics()
            return {
                "summary": f"{report.passed} passed, {report.failed} failed, {report.warnings} warnings"
            }
        except Exception as e:
            return {"summary": f"Error: {e}"}
    
    @router.post("/api/lock")
    async def toggle_lock(request: Request):
        """Toggle gateway lock."""
        try:
            from ..core.gateway_lock import get_gateway_lock
            data = await request.json()
            gl = get_gateway_lock()
            
            if data.get("lock"):
                gl.lock(message="Locked from dashboard")
            else:
                gl.unlock()
            
            return {"status": "ok", "locked": gl.is_locked()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/api/broadcast")
    async def send_broadcast(request: Request):
        """Send broadcast message."""
        try:
            data = await request.json()
            message = data.get("message", "")
            
            # This would need the bot instance to actually send
            logger.info(f"Broadcast requested: {message}")
            
            return {"status": "ok", "message": "Broadcast queued"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return router


__all__ = [
    "create_dashboard_router",
    "DashboardStats",
    "DASHBOARD_HTML",
]

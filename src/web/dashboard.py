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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Inter', 'sans-serif'] },
                    animation: {
                        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                        'gradient': 'gradient 8s ease infinite',
                    },
                    keyframes: {
                        gradient: {
                            '0%, 100%': { backgroundPosition: '0% 50%' },
                            '50%': { backgroundPosition: '100% 50%' },
                        }
                    }
                }
            }
        }
    </script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        .gradient-bg { 
            background: linear-gradient(-45deg, #667eea, #764ba2, #6B8DD6, #8E37D7);
            background-size: 400% 400%;
            animation: gradient 15s ease infinite;
        }
        .glass { 
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
        }
        .card-hover { transition: all 0.3s ease; }
        .card-hover:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(0,0,0,0.12); }
        .progress-bar { transition: width 0.5s ease; }
        .status-dot { animation: pulse 2s infinite; }
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
    </style>
</head>
<body class="bg-slate-50 min-h-screen" x-data="dashboard()">
    <!-- Header -->
    <nav class="gradient-bg shadow-xl sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <div class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
                        <span class="text-2xl">🤖</span>
                    </div>
                    <div>
                        <h1 class="text-xl font-bold text-white">CursorBot</h1>
                        <p class="text-white/60 text-xs">Dashboard v0.3</p>
                    </div>
                </div>
                <div class="flex items-center space-x-6">
                    <div class="hidden md:flex items-center space-x-2 text-white/80 text-sm">
                        <span>🕐</span>
                        <span x-text="currentTime"></span>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span class="status-dot w-2 h-2 rounded-full"
                              :class="status === 'online' ? 'bg-green-400' : 'bg-red-400'"></span>
                        <span class="px-3 py-1.5 rounded-lg text-sm font-medium"
                              :class="status === 'online' ? 'bg-green-400/20 text-green-100' : 'bg-red-400/20 text-red-100'"
                              x-text="status === 'online' ? '線上運行' : '離線'"></span>
                    </div>
                    <a href="/chat" class="px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-lg text-sm font-medium transition">
                        💬 WebChat
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-6 py-8">
        <!-- Stats Cards Row 1 -->
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
            <div class="glass rounded-2xl shadow-lg p-5 card-hover border border-white/50">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-2xl">⏱️</span>
                    <span class="text-xs text-green-500 font-medium bg-green-50 px-2 py-1 rounded-full">運行中</span>
                </div>
                <p class="text-slate-500 text-xs mb-1">運行時間</p>
                <p class="text-xl font-bold text-slate-800" x-text="stats.uptime"></p>
            </div>
            <div class="glass rounded-2xl shadow-lg p-5 card-hover border border-white/50">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-2xl">💬</span>
                </div>
                <p class="text-slate-500 text-xs mb-1">活躍會話</p>
                <p class="text-xl font-bold text-slate-800" x-text="stats.active_sessions"></p>
            </div>
            <div class="glass rounded-2xl shadow-lg p-5 card-hover border border-white/50">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-2xl">👥</span>
                </div>
                <p class="text-slate-500 text-xs mb-1">總用戶數</p>
                <p class="text-xl font-bold text-slate-800" x-text="stats.total_users"></p>
            </div>
            <div class="glass rounded-2xl shadow-lg p-5 card-hover border border-white/50">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-2xl">📨</span>
                </div>
                <p class="text-slate-500 text-xs mb-1">總訊息數</p>
                <p class="text-xl font-bold text-slate-800" x-text="stats.total_messages"></p>
            </div>
            <div class="glass rounded-2xl shadow-lg p-5 card-hover border border-white/50">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-2xl">🧠</span>
                </div>
                <p class="text-slate-500 text-xs mb-1">LLM 呼叫</p>
                <p class="text-xl font-bold text-slate-800" x-text="stats.llm_calls"></p>
            </div>
            <div class="glass rounded-2xl shadow-lg p-5 card-hover border border-white/50">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-2xl">🤖</span>
                </div>
                <p class="text-slate-500 text-xs mb-1">當前模型</p>
                <p class="text-sm font-bold text-slate-800 truncate" x-text="stats.current_model"></p>
            </div>
        </div>

        <!-- System Resources -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div class="glass rounded-2xl shadow-lg p-6 card-hover border border-white/50">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="font-semibold text-slate-800">💻 CPU 使用率</h3>
                    <span class="text-2xl font-bold" :class="system.cpu > 80 ? 'text-red-500' : 'text-green-500'" x-text="system.cpu + '%'"></span>
                </div>
                <div class="w-full bg-slate-200 rounded-full h-3">
                    <div class="h-3 rounded-full progress-bar" 
                         :class="system.cpu > 80 ? 'bg-red-500' : system.cpu > 50 ? 'bg-yellow-500' : 'bg-green-500'"
                         :style="'width: ' + system.cpu + '%'"></div>
                </div>
            </div>
            <div class="glass rounded-2xl shadow-lg p-6 card-hover border border-white/50">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="font-semibold text-slate-800">🧮 記憶體使用</h3>
                    <span class="text-2xl font-bold" :class="system.memory > 80 ? 'text-red-500' : 'text-green-500'" x-text="system.memory + '%'"></span>
                </div>
                <div class="w-full bg-slate-200 rounded-full h-3">
                    <div class="h-3 rounded-full progress-bar"
                         :class="system.memory > 80 ? 'bg-red-500' : system.memory > 50 ? 'bg-yellow-500' : 'bg-green-500'"
                         :style="'width: ' + system.memory + '%'"></div>
                </div>
                <p class="text-xs text-slate-500 mt-2" x-text="system.memory_detail"></p>
            </div>
            <div class="glass rounded-2xl shadow-lg p-6 card-hover border border-white/50">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="font-semibold text-slate-800">💾 磁碟空間</h3>
                    <span class="text-2xl font-bold" :class="system.disk > 90 ? 'text-red-500' : 'text-green-500'" x-text="system.disk + '%'"></span>
                </div>
                <div class="w-full bg-slate-200 rounded-full h-3">
                    <div class="h-3 rounded-full progress-bar"
                         :class="system.disk > 90 ? 'bg-red-500' : system.disk > 70 ? 'bg-yellow-500' : 'bg-green-500'"
                         :style="'width: ' + system.disk + '%'"></div>
                </div>
                <p class="text-xs text-slate-500 mt-2" x-text="system.disk_detail"></p>
            </div>
        </div>

        <!-- Main Content Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <!-- Sessions Panel -->
            <div class="lg:col-span-2 glass rounded-2xl shadow-lg overflow-hidden card-hover border border-white/50">
                <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-gradient-to-r from-blue-50 to-purple-50">
                    <h2 class="text-lg font-semibold text-slate-800 flex items-center gap-2">
                        <span>📋</span> 活躍會話
                    </h2>
                    <button @click="refreshSessions()" class="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition flex items-center gap-1">
                        <span>🔄</span> 重新整理
                    </button>
                </div>
                <div class="p-6">
                    <div class="overflow-x-auto">
                        <table class="w-full">
                            <thead>
                                <tr class="text-left text-slate-500 text-sm border-b border-slate-100">
                                    <th class="pb-3 font-medium">用戶 ID</th>
                                    <th class="pb-3 font-medium">訊息數</th>
                                    <th class="pb-3 font-medium">最後活動</th>
                                    <th class="pb-3 font-medium">操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                <template x-for="session in sessions" :key="session.session_key">
                                    <tr class="border-b border-slate-50 hover:bg-slate-50 transition">
                                        <td class="py-3">
                                            <span class="px-2 py-1 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium" x-text="session.user_id"></span>
                                        </td>
                                        <td class="py-3">
                                            <span class="font-semibold" x-text="session.messages"></span>
                                        </td>
                                        <td class="py-3 text-slate-500 text-sm" x-text="session.last_activity"></td>
                                        <td class="py-3">
                                            <button @click="clearSession(session.session_key)"
                                                    class="px-3 py-1 bg-red-100 hover:bg-red-200 text-red-600 rounded-lg text-sm font-medium transition">
                                                清除
                                            </button>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                        <div x-show="sessions.length === 0" class="text-center py-12">
                            <span class="text-4xl mb-4 block">📭</span>
                            <p class="text-slate-500">目前沒有活躍會話</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Actions & Providers -->
            <div class="space-y-6">
                <!-- Quick Actions -->
                <div class="glass rounded-2xl shadow-lg overflow-hidden card-hover border border-white/50">
                    <div class="px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-orange-50 to-yellow-50">
                        <h2 class="text-lg font-semibold text-slate-800 flex items-center gap-2">
                            <span>⚡</span> 快速操作
                        </h2>
                    </div>
                    <div class="p-4 space-y-3">
                        <button @click="runDoctor()" 
                                class="w-full py-3 px-4 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-xl font-medium transition shadow-lg shadow-blue-500/25 flex items-center justify-center gap-2">
                            <span>🩺</span> 系統診斷
                        </button>
                        <button @click="clearAllSessions()"
                                class="w-full py-3 px-4 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white rounded-xl font-medium transition shadow-lg shadow-orange-500/25 flex items-center justify-center gap-2">
                            <span>🗑️</span> 清除所有會話
                        </button>
                        <button @click="toggleLock()"
                                class="w-full py-3 px-4 rounded-xl font-medium transition shadow-lg flex items-center justify-center gap-2"
                                :class="locked ? 'bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white shadow-green-500/25' : 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white shadow-red-500/25'">
                            <span x-text="locked ? '🔓' : '🔒'"></span>
                            <span x-text="locked ? '解除鎖定' : '鎖定 Bot'"></span>
                        </button>
                    </div>
                </div>

                <!-- AI Providers -->
                <div class="glass rounded-2xl shadow-lg overflow-hidden card-hover border border-white/50">
                    <div class="px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-purple-50 to-pink-50">
                        <h2 class="text-lg font-semibold text-slate-800 flex items-center gap-2">
                            <span>🤖</span> AI 提供者
                        </h2>
                    </div>
                    <div class="p-4 space-y-2">
                        <template x-for="(info, name) in providers" :key="name">
                            <div class="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                                <div class="flex items-center gap-3">
                                    <span class="w-2 h-2 rounded-full" :class="info.available ? 'bg-green-500' : 'bg-slate-300'"></span>
                                    <span class="font-medium text-slate-700 capitalize" x-text="name"></span>
                                </div>
                                <span class="text-xs px-2 py-1 rounded-lg" 
                                      :class="info.available ? 'bg-green-100 text-green-700' : 'bg-slate-200 text-slate-500'"
                                      x-text="info.available ? '可用' : '未設定'"></span>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
        </div>

        <!-- System Diagnostics -->
        <div class="glass rounded-2xl shadow-lg overflow-hidden card-hover border border-white/50 mb-6">
            <div class="px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-green-50 to-teal-50 flex justify-between items-center">
                <h2 class="text-lg font-semibold text-slate-800 flex items-center gap-2">
                    <span>🩺</span> 系統診斷
                </h2>
                <button @click="runDoctor()" class="px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition">
                    重新診斷
                </button>
            </div>
            <div class="p-6">
                <div class="flex items-center gap-6 mb-6">
                    <div class="flex items-center gap-4">
                        <div class="text-center">
                            <div class="text-3xl font-bold text-green-500" x-text="diagnostics.passed"></div>
                            <div class="text-xs text-slate-500">通過</div>
                        </div>
                        <div class="text-center">
                            <div class="text-3xl font-bold text-yellow-500" x-text="diagnostics.warnings"></div>
                            <div class="text-xs text-slate-500">警告</div>
                        </div>
                        <div class="text-center">
                            <div class="text-3xl font-bold text-red-500" x-text="diagnostics.failed"></div>
                            <div class="text-xs text-slate-500">失敗</div>
                        </div>
                    </div>
                    <div class="flex-1">
                        <div class="flex gap-1 h-4 rounded-full overflow-hidden bg-slate-200">
                            <div class="bg-green-500 transition-all" :style="'width: ' + (diagnostics.passed / diagnostics.total * 100) + '%'"></div>
                            <div class="bg-yellow-500 transition-all" :style="'width: ' + (diagnostics.warnings / diagnostics.total * 100) + '%'"></div>
                            <div class="bg-red-500 transition-all" :style="'width: ' + (diagnostics.failed / diagnostics.total * 100) + '%'"></div>
                        </div>
                    </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    <template x-for="result in diagnostics.results" :key="result.name">
                        <div class="p-3 rounded-xl border" 
                             :class="{
                                 'bg-green-50 border-green-200': result.level === 'ok',
                                 'bg-yellow-50 border-yellow-200': result.level === 'warning',
                                 'bg-red-50 border-red-200': result.level === 'error' || result.level === 'critical',
                                 'bg-blue-50 border-blue-200': result.level === 'info'
                             }">
                            <div class="flex items-center gap-2 mb-1">
                                <span x-text="result.level === 'ok' ? '✅' : result.level === 'warning' ? '⚠️' : result.level === 'info' ? 'ℹ️' : '❌'"></span>
                                <span class="font-medium text-sm text-slate-700" x-text="result.name"></span>
                            </div>
                            <p class="text-xs text-slate-600" x-text="result.message"></p>
                        </div>
                    </template>
                </div>
            </div>
        </div>

        <!-- Broadcast -->
        <div class="glass rounded-2xl shadow-lg overflow-hidden card-hover border border-white/50">
            <div class="px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-indigo-50 to-blue-50">
                <h2 class="text-lg font-semibold text-slate-800 flex items-center gap-2">
                    <span>📢</span> 發送廣播訊息
                </h2>
            </div>
            <div class="p-6">
                <div class="flex gap-4">
                    <textarea x-model="broadcastMsg" 
                              class="flex-1 p-4 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent transition resize-none"
                              placeholder="輸入要發送給所有用戶的訊息..."
                              rows="3"></textarea>
                    <button @click="sendBroadcast()"
                            class="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white rounded-xl font-medium transition shadow-lg shadow-indigo-500/25 self-end">
                        發送
                    </button>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="mt-8 py-8 text-center border-t border-slate-200 bg-white">
        <p class="text-slate-500 text-sm">CursorBot v0.3 Dashboard</p>
        <p class="text-slate-400 text-xs mt-1">Built with FastAPI, Alpine.js & TailwindCSS</p>
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
                system: {
                    cpu: 0,
                    memory: 0,
                    memory_detail: '',
                    disk: 0,
                    disk_detail: ''
                },
                providers: {},
                diagnostics: {
                    passed: 0,
                    warnings: 0,
                    failed: 0,
                    total: 1,
                    results: []
                },
                sessions: [],
                
                init() {
                    this.updateTime();
                    setInterval(() => this.updateTime(), 1000);
                    this.fetchAll();
                    setInterval(() => this.fetchAll(), 10000);
                },
                
                updateTime() {
                    this.currentTime = new Date().toLocaleString('zh-TW');
                },
                
                async fetchAll() {
                    await Promise.all([
                        this.fetchStats(),
                        this.fetchSessions(),
                        this.fetchSystem(),
                        this.fetchProviders(),
                        this.fetchDiagnostics()
                    ]);
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
                    } catch (e) {}
                },
                
                async fetchSystem() {
                    try {
                        const res = await fetch('/dashboard/api/system');
                        if (res.ok) {
                            this.system = await res.json();
                        }
                    } catch (e) {}
                },
                
                async fetchProviders() {
                    try {
                        const res = await fetch('/dashboard/api/providers');
                        if (res.ok) {
                            this.providers = await res.json();
                        }
                    } catch (e) {}
                },
                
                async fetchDiagnostics() {
                    try {
                        const res = await fetch('/dashboard/api/diagnostics');
                        if (res.ok) {
                            this.diagnostics = await res.json();
                        }
                    } catch (e) {}
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
                    if (!confirm('確定要清除所有會話？此操作無法復原！')) return;
                    try {
                        await fetch('/dashboard/api/sessions', { method: 'DELETE' });
                        this.fetchSessions();
                    } catch (e) {
                        alert('清除失敗');
                    }
                },
                
                async runDoctor() {
                    try {
                        await this.fetchDiagnostics();
                        alert(`診斷完成！\\n通過: ${this.diagnostics.passed}\\n警告: ${this.diagnostics.warnings}\\n失敗: ${this.diagnostics.failed}`);
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
                    if (!confirm('確定要發送此廣播訊息給所有用戶？')) return;
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
                "current_model": llm_manager.get_current_status().get("current_model") or "default",
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
    
    @router.get("/api/system")
    async def get_system_info():
        """Get system resource information."""
        try:
            import psutil
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory
            mem = psutil.virtual_memory()
            mem_used_gb = mem.used / (1024 ** 3)
            mem_total_gb = mem.total / (1024 ** 3)
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024 ** 3)
            disk_total_gb = disk.total / (1024 ** 3)
            
            return {
                "cpu": round(cpu_percent, 1),
                "memory": round(mem.percent, 1),
                "memory_detail": f"{mem_used_gb:.1f}GB / {mem_total_gb:.1f}GB",
                "disk": round(disk.percent, 1),
                "disk_detail": f"{disk_used_gb:.1f}GB / {disk_total_gb:.1f}GB",
            }
        except Exception as e:
            logger.error(f"System info error: {e}")
            return {
                "cpu": 0,
                "memory": 0,
                "memory_detail": "N/A",
                "disk": 0,
                "disk_detail": "N/A",
            }
    
    @router.get("/api/providers")
    async def get_providers():
        """Get AI provider status."""
        try:
            from ..core.llm_providers import get_llm_manager
            manager = get_llm_manager()
            
            # Get provider status
            available = manager.list_available_providers()
            status = manager.get_current_status()
            
            result = {}
            for provider in ["openai", "anthropic", "google", "openrouter", "ollama", "bedrock", "moonshot", "glm"]:
                result[provider] = {
                    "available": provider in available,
                    "current": provider == status.get("current_provider"),
                }
            
            return result
        except Exception as e:
            logger.error(f"Providers error: {e}")
            return {}
    
    @router.get("/api/diagnostics")
    async def get_diagnostics():
        """Get detailed diagnostics."""
        try:
            from ..core.doctor import run_diagnostics
            report = await run_diagnostics()
            
            results = []
            for r in report.results:
                results.append({
                    "name": r.name,
                    "level": r.level.value,
                    "message": r.message,
                    "recommendation": r.recommendation or "",
                })
            
            return {
                "passed": report.passed,
                "warnings": report.warnings,
                "failed": report.failed,
                "total": len(report.results) or 1,
                "results": results,
            }
        except Exception as e:
            logger.error(f"Diagnostics error: {e}")
            return {
                "passed": 0,
                "warnings": 0,
                "failed": 1,
                "total": 1,
                "results": [{"name": "Error", "level": "error", "message": str(e), "recommendation": ""}],
            }
    
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

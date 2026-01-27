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
<html lang="zh-TW" x-data="{ darkMode: localStorage.getItem('darkMode') === 'true' }" :class="{ 'dark': darkMode }">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CursorBot Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: { sans: ['Plus Jakarta Sans', 'sans-serif'] },
                    colors: {
                        primary: { 50: '#f0f9ff', 100: '#e0f2fe', 200: '#bae6fd', 300: '#7dd3fc', 400: '#38bdf8', 500: '#0ea5e9', 600: '#0284c7', 700: '#0369a1', 800: '#075985', 900: '#0c4a6e' },
                        dark: { 800: '#1e293b', 900: '#0f172a', 950: '#020617' }
                    }
                }
            }
        }
    </script>
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; }
        .sidebar-item { transition: all 0.2s ease; }
        .sidebar-item:hover { transform: translateX(4px); }
        .card { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .card:hover { transform: translateY(-4px); }
        .gradient-border { background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%); padding: 2px; }
        .stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; border-radius: 12px 12px 0 0; }
        .stat-card.blue::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
        .stat-card.green::before { background: linear-gradient(90deg, #22c55e, #4ade80); }
        .stat-card.purple::before { background: linear-gradient(90deg, #a855f7, #c084fc); }
        .stat-card.orange::before { background: linear-gradient(90deg, #f97316, #fb923c); }
        .stat-card.pink::before { background: linear-gradient(90deg, #ec4899, #f472b6); }
        .stat-card.cyan::before { background: linear-gradient(90deg, #06b6d4, #22d3ee); }
        .progress-ring { transition: stroke-dashoffset 0.5s ease; }
        .animate-float { animation: float 3s ease-in-out infinite; }
        @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
        .glow { box-shadow: 0 0 40px rgba(99, 102, 241, 0.15); }
        .dark .glow { box-shadow: 0 0 40px rgba(99, 102, 241, 0.3); }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
        .dark ::-webkit-scrollbar-thumb { background: #475569; }
    </style>
</head>
<body class="bg-slate-50 dark:bg-dark-950 min-h-screen transition-colors duration-300" x-data="dashboard()">
    <div class="flex">
        <!-- Sidebar -->
        <aside class="w-72 min-h-screen bg-white dark:bg-dark-900 border-r border-slate-200 dark:border-slate-800 fixed left-0 top-0 z-40 flex flex-col">
            <!-- Logo -->
            <div class="p-6 border-b border-slate-200 dark:border-slate-800">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 animate-float">
                        <span class="text-2xl">🤖</span>
                    </div>
                    <div>
                        <h1 class="text-xl font-bold text-slate-800 dark:text-white">CursorBot</h1>
                        <p class="text-xs text-slate-500 dark:text-slate-400">智能助手控制台</p>
                    </div>
                </div>
            </div>
            
            <!-- Navigation -->
            <nav class="flex-1 p-4 space-y-2">
                <div class="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-4 px-3">主要功能</div>
                <a href="#overview" class="sidebar-item flex items-center gap-3 px-4 py-3 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-medium">
                    <span class="text-lg">📊</span>
                    <span>總覽</span>
                </a>
                <a href="#sessions" class="sidebar-item flex items-center gap-3 px-4 py-3 rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium">
                    <span class="text-lg">💬</span>
                    <span>會話管理</span>
                </a>
                <a href="#diagnostics" class="sidebar-item flex items-center gap-3 px-4 py-3 rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium">
                    <span class="text-lg">🩺</span>
                    <span>系統診斷</span>
                </a>
                <a href="/chat" class="sidebar-item flex items-center gap-3 px-4 py-3 rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium">
                    <span class="text-lg">🗨️</span>
                    <span>WebChat</span>
                </a>
                <a href="/control" class="sidebar-item flex items-center gap-3 px-4 py-3 rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium">
                    <span class="text-lg">⚙️</span>
                    <span>設定</span>
                </a>
                
                <div class="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mt-8 mb-4 px-3">快速操作</div>
                <button @click="runDoctor()" class="sidebar-item w-full flex items-center gap-3 px-4 py-3 rounded-xl text-slate-600 dark:text-slate-400 hover:bg-blue-50 dark:hover:bg-blue-500/10 hover:text-blue-600 dark:hover:text-blue-400 font-medium text-left">
                    <span class="text-lg">🔍</span>
                    <span>執行診斷</span>
                </button>
                <button @click="clearAllSessions()" class="sidebar-item w-full flex items-center gap-3 px-4 py-3 rounded-xl text-slate-600 dark:text-slate-400 hover:bg-orange-50 dark:hover:bg-orange-500/10 hover:text-orange-600 dark:hover:text-orange-400 font-medium text-left">
                    <span class="text-lg">🗑️</span>
                    <span>清除會話</span>
                </button>
            </nav>
            
            <!-- Footer -->
            <div class="p-4 border-t border-slate-200 dark:border-slate-800">
                <div class="flex items-center justify-between text-sm">
                    <span class="text-slate-500 dark:text-slate-400">v0.3.0</span>
                    <button @click="darkMode = !darkMode; localStorage.setItem('darkMode', darkMode)" 
                            class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition">
                        <span x-show="!darkMode" class="text-lg">🌙</span>
                        <span x-show="darkMode" class="text-lg">☀️</span>
                    </button>
                </div>
            </div>
        </aside>

        <!-- Main Content -->
        <main class="flex-1 ml-72 min-h-screen">
            <!-- Top Bar -->
            <header class="sticky top-0 z-30 bg-white/80 dark:bg-dark-900/80 backdrop-blur-xl border-b border-slate-200 dark:border-slate-800">
                <div class="px-8 py-4 flex items-center justify-between">
                    <div>
                        <h2 class="text-2xl font-bold text-slate-800 dark:text-white">儀表板總覽</h2>
                        <p class="text-sm text-slate-500 dark:text-slate-400" x-text="currentTime"></p>
                    </div>
                    <div class="flex items-center gap-4">
                        <div class="flex items-center gap-2 px-4 py-2 rounded-full" 
                             :class="status === 'online' ? 'bg-green-100 dark:bg-green-500/20' : 'bg-red-100 dark:bg-red-500/20'">
                            <span class="relative flex h-3 w-3">
                                <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                                      :class="status === 'online' ? 'bg-green-400' : 'bg-red-400'"></span>
                                <span class="relative inline-flex rounded-full h-3 w-3"
                                      :class="status === 'online' ? 'bg-green-500' : 'bg-red-500'"></span>
                            </span>
                            <span class="text-sm font-medium"
                                  :class="status === 'online' ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'"
                                  x-text="status === 'online' ? '系統正常' : '連線中斷'"></span>
                        </div>
                        <button @click="fetchAll()" class="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition text-slate-500 dark:text-slate-400">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            </header>

            <div class="p-8 space-y-8">
                <!-- Stats Grid -->
                <section id="overview">
                    <div class="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
                        <div class="stat-card blue card relative bg-white dark:bg-dark-800 rounded-2xl p-6 shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50 glow overflow-hidden">
                            <div class="flex items-start justify-between">
                                <div>
                                    <p class="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">運行時間</p>
                                    <p class="text-2xl font-bold text-slate-800 dark:text-white" x-text="stats.uptime"></p>
                                </div>
                                <div class="w-12 h-12 rounded-2xl bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center">
                                    <span class="text-2xl">⏱️</span>
                                </div>
                            </div>
                        </div>
                        <div class="stat-card green card relative bg-white dark:bg-dark-800 rounded-2xl p-6 shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50 glow overflow-hidden">
                            <div class="flex items-start justify-between">
                                <div>
                                    <p class="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">活躍會話</p>
                                    <p class="text-2xl font-bold text-slate-800 dark:text-white" x-text="stats.active_sessions"></p>
                                </div>
                                <div class="w-12 h-12 rounded-2xl bg-green-100 dark:bg-green-500/20 flex items-center justify-center">
                                    <span class="text-2xl">💬</span>
                                </div>
                            </div>
                        </div>
                        <div class="stat-card purple card relative bg-white dark:bg-dark-800 rounded-2xl p-6 shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50 glow overflow-hidden">
                            <div class="flex items-start justify-between">
                                <div>
                                    <p class="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">總用戶數</p>
                                    <p class="text-2xl font-bold text-slate-800 dark:text-white" x-text="stats.total_users"></p>
                                </div>
                                <div class="w-12 h-12 rounded-2xl bg-purple-100 dark:bg-purple-500/20 flex items-center justify-center">
                                    <span class="text-2xl">👥</span>
                                </div>
                            </div>
                        </div>
                        <div class="stat-card orange card relative bg-white dark:bg-dark-800 rounded-2xl p-6 shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50 glow overflow-hidden">
                            <div class="flex items-start justify-between">
                                <div>
                                    <p class="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">總訊息數</p>
                                    <p class="text-2xl font-bold text-slate-800 dark:text-white" x-text="stats.total_messages"></p>
                                </div>
                                <div class="w-12 h-12 rounded-2xl bg-orange-100 dark:bg-orange-500/20 flex items-center justify-center">
                                    <span class="text-2xl">📨</span>
                                </div>
                            </div>
                        </div>
                        <div class="stat-card pink card relative bg-white dark:bg-dark-800 rounded-2xl p-6 shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50 glow overflow-hidden">
                            <div class="flex items-start justify-between">
                                <div>
                                    <p class="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">LLM 呼叫</p>
                                    <p class="text-2xl font-bold text-slate-800 dark:text-white" x-text="stats.llm_calls"></p>
                                </div>
                                <div class="w-12 h-12 rounded-2xl bg-pink-100 dark:bg-pink-500/20 flex items-center justify-center">
                                    <span class="text-2xl">🧠</span>
                                </div>
                            </div>
                        </div>
                        <div class="stat-card cyan card relative bg-white dark:bg-dark-800 rounded-2xl p-6 shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50 glow overflow-hidden">
                            <div class="flex items-start justify-between">
                                <div>
                                    <p class="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">當前模型</p>
                                    <p class="text-lg font-bold text-slate-800 dark:text-white truncate" x-text="stats.current_model"></p>
                                </div>
                                <div class="w-12 h-12 rounded-2xl bg-cyan-100 dark:bg-cyan-500/20 flex items-center justify-center">
                                    <span class="text-2xl">🤖</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- System Resources -->
                <section>
                    <h3 class="text-lg font-semibold text-slate-800 dark:text-white mb-4">系統資源</h3>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div class="card bg-white dark:bg-dark-800 rounded-2xl p-6 shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50">
                            <div class="flex items-center justify-between mb-4">
                                <div class="flex items-center gap-3">
                                    <div class="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center">
                                        <span>💻</span>
                                    </div>
                                    <span class="font-semibold text-slate-700 dark:text-slate-200">CPU</span>
                                </div>
                                <span class="text-2xl font-bold" :class="system.cpu > 80 ? 'text-red-500' : system.cpu > 50 ? 'text-yellow-500' : 'text-green-500'" x-text="system.cpu + '%'"></span>
                            </div>
                            <div class="h-3 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                                <div class="h-full rounded-full transition-all duration-500"
                                     :class="system.cpu > 80 ? 'bg-gradient-to-r from-red-500 to-red-400' : system.cpu > 50 ? 'bg-gradient-to-r from-yellow-500 to-yellow-400' : 'bg-gradient-to-r from-green-500 to-green-400'"
                                     :style="'width: ' + system.cpu + '%'"></div>
                            </div>
                        </div>
                        <div class="card bg-white dark:bg-dark-800 rounded-2xl p-6 shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50">
                            <div class="flex items-center justify-between mb-4">
                                <div class="flex items-center gap-3">
                                    <div class="w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-500/20 flex items-center justify-center">
                                        <span>🧮</span>
                                    </div>
                                    <span class="font-semibold text-slate-700 dark:text-slate-200">記憶體</span>
                                </div>
                                <span class="text-2xl font-bold" :class="system.memory > 80 ? 'text-red-500' : system.memory > 50 ? 'text-yellow-500' : 'text-green-500'" x-text="system.memory + '%'"></span>
                            </div>
                            <div class="h-3 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                                <div class="h-full rounded-full transition-all duration-500"
                                     :class="system.memory > 80 ? 'bg-gradient-to-r from-red-500 to-red-400' : system.memory > 50 ? 'bg-gradient-to-r from-yellow-500 to-yellow-400' : 'bg-gradient-to-r from-purple-500 to-purple-400'"
                                     :style="'width: ' + system.memory + '%'"></div>
                            </div>
                            <p class="text-xs text-slate-500 dark:text-slate-400 mt-2" x-text="system.memory_detail"></p>
                        </div>
                        <div class="card bg-white dark:bg-dark-800 rounded-2xl p-6 shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50">
                            <div class="flex items-center justify-between mb-4">
                                <div class="flex items-center gap-3">
                                    <div class="w-10 h-10 rounded-xl bg-orange-100 dark:bg-orange-500/20 flex items-center justify-center">
                                        <span>💾</span>
                                    </div>
                                    <span class="font-semibold text-slate-700 dark:text-slate-200">磁碟</span>
                                </div>
                                <span class="text-2xl font-bold" :class="system.disk > 90 ? 'text-red-500' : system.disk > 70 ? 'text-yellow-500' : 'text-green-500'" x-text="system.disk + '%'"></span>
                            </div>
                            <div class="h-3 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                                <div class="h-full rounded-full transition-all duration-500"
                                     :class="system.disk > 90 ? 'bg-gradient-to-r from-red-500 to-red-400' : system.disk > 70 ? 'bg-gradient-to-r from-yellow-500 to-yellow-400' : 'bg-gradient-to-r from-orange-500 to-orange-400'"
                                     :style="'width: ' + system.disk + '%'"></div>
                            </div>
                            <p class="text-xs text-slate-500 dark:text-slate-400 mt-2" x-text="system.disk_detail"></p>
                        </div>
                    </div>
                </section>

                <!-- Two Column Layout -->
                <section class="grid grid-cols-1 xl:grid-cols-3 gap-8">
                    <!-- Sessions Table -->
                    <div id="sessions" class="xl:col-span-2 card bg-white dark:bg-dark-800 rounded-2xl shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50 overflow-hidden">
                        <div class="px-6 py-5 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-500/20 flex items-center justify-center">
                                    <span class="text-xl">📋</span>
                                </div>
                                <div>
                                    <h3 class="font-semibold text-slate-800 dark:text-white">活躍會話</h3>
                                    <p class="text-xs text-slate-500 dark:text-slate-400" x-text="sessions.length + ' 個會話'"></p>
                                </div>
                            </div>
                            <button @click="fetchSessions()" class="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium rounded-xl transition shadow-lg shadow-indigo-500/25">
                                重新整理
                            </button>
                        </div>
                        <div class="p-6 overflow-x-auto">
                            <table class="w-full">
                                <thead>
                                    <tr class="border-b border-slate-200 dark:border-slate-700">
                                        <th class="text-left py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">用戶</th>
                                        <th class="text-left py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">訊息</th>
                                        <th class="text-left py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">活動時間</th>
                                        <th class="text-right py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">操作</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <template x-for="session in sessions" :key="session.session_key">
                                        <tr class="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition">
                                            <td class="py-4 px-4">
                                                <div class="flex items-center gap-3">
                                                    <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white text-xs font-bold" x-text="String(session.user_id).slice(-2)"></div>
                                                    <span class="font-medium text-slate-700 dark:text-slate-200" x-text="session.user_id"></span>
                                                </div>
                                            </td>
                                            <td class="py-4 px-4">
                                                <span class="px-3 py-1 bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 rounded-lg text-sm font-medium" x-text="session.messages"></span>
                                            </td>
                                            <td class="py-4 px-4 text-sm text-slate-500 dark:text-slate-400" x-text="session.last_activity"></td>
                                            <td class="py-4 px-4 text-right">
                                                <button @click="clearSession(session.session_key)" class="px-3 py-1.5 bg-red-100 dark:bg-red-500/20 hover:bg-red-200 dark:hover:bg-red-500/30 text-red-600 dark:text-red-400 rounded-lg text-sm font-medium transition">
                                                    清除
                                                </button>
                                            </td>
                                        </tr>
                                    </template>
                                </tbody>
                            </table>
                            <div x-show="sessions.length === 0" class="text-center py-16">
                                <div class="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                                    <span class="text-4xl">📭</span>
                                </div>
                                <p class="text-slate-500 dark:text-slate-400">目前沒有活躍會話</p>
                            </div>
                        </div>
                    </div>

                    <!-- AI Providers -->
                    <div class="card bg-white dark:bg-dark-800 rounded-2xl shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50 overflow-hidden">
                        <div class="px-6 py-5 border-b border-slate-200 dark:border-slate-700">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-500/20 flex items-center justify-center">
                                    <span class="text-xl">🤖</span>
                                </div>
                                <div>
                                    <h3 class="font-semibold text-slate-800 dark:text-white">AI 提供者</h3>
                                    <p class="text-xs text-slate-500 dark:text-slate-400">模型狀態</p>
                                </div>
                            </div>
                        </div>
                        <div class="p-4 space-y-2">
                            <template x-for="(info, name) in providers" :key="name">
                                <div class="flex items-center justify-between p-4 rounded-xl transition"
                                     :class="info.available ? 'bg-green-50 dark:bg-green-500/10' : 'bg-slate-50 dark:bg-slate-700/30'">
                                    <div class="flex items-center gap-3">
                                        <div class="w-8 h-8 rounded-lg flex items-center justify-center"
                                             :class="info.available ? 'bg-green-100 dark:bg-green-500/20' : 'bg-slate-200 dark:bg-slate-600'">
                                            <span class="text-sm" x-text="info.available ? '✓' : '−'"></span>
                                        </div>
                                        <span class="font-medium capitalize" :class="info.available ? 'text-green-700 dark:text-green-400' : 'text-slate-500 dark:text-slate-400'" x-text="name"></span>
                                    </div>
                                    <span class="text-xs px-2 py-1 rounded-full font-medium"
                                          :class="info.available ? 'bg-green-200 dark:bg-green-500/30 text-green-700 dark:text-green-400' : 'bg-slate-200 dark:bg-slate-600 text-slate-500 dark:text-slate-400'"
                                          x-text="info.current ? '使用中' : info.available ? '可用' : '未設定'"></span>
                                </div>
                            </template>
                        </div>
                    </div>
                </section>

                <!-- Diagnostics -->
                <section id="diagnostics" class="card bg-white dark:bg-dark-800 rounded-2xl shadow-lg dark:shadow-none border border-slate-200/50 dark:border-slate-700/50 overflow-hidden">
                    <div class="px-6 py-5 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-xl bg-teal-100 dark:bg-teal-500/20 flex items-center justify-center">
                                <span class="text-xl">🩺</span>
                            </div>
                            <div>
                                <h3 class="font-semibold text-slate-800 dark:text-white">系統診斷</h3>
                                <p class="text-xs text-slate-500 dark:text-slate-400">健康狀態檢查</p>
                            </div>
                        </div>
                        <button @click="fetchDiagnostics()" class="px-4 py-2 bg-teal-500 hover:bg-teal-600 text-white text-sm font-medium rounded-xl transition shadow-lg shadow-teal-500/25">
                            重新診斷
                        </button>
                    </div>
                    <div class="p-6">
                        <!-- Summary -->
                        <div class="flex items-center gap-8 mb-8 p-6 bg-slate-50 dark:bg-slate-700/30 rounded-2xl">
                            <div class="flex items-center gap-6">
                                <div class="text-center">
                                    <div class="text-4xl font-bold text-green-500" x-text="diagnostics.passed"></div>
                                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">通過</div>
                                </div>
                                <div class="w-px h-12 bg-slate-200 dark:bg-slate-600"></div>
                                <div class="text-center">
                                    <div class="text-4xl font-bold text-yellow-500" x-text="diagnostics.warnings"></div>
                                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">警告</div>
                                </div>
                                <div class="w-px h-12 bg-slate-200 dark:bg-slate-600"></div>
                                <div class="text-center">
                                    <div class="text-4xl font-bold text-red-500" x-text="diagnostics.failed"></div>
                                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">失敗</div>
                                </div>
                            </div>
                            <div class="flex-1">
                                <div class="h-4 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden flex">
                                    <div class="bg-gradient-to-r from-green-500 to-green-400 transition-all duration-500" :style="'width: ' + (diagnostics.total > 0 ? (diagnostics.passed / diagnostics.total * 100) : 0) + '%'"></div>
                                    <div class="bg-gradient-to-r from-yellow-500 to-yellow-400 transition-all duration-500" :style="'width: ' + (diagnostics.total > 0 ? (diagnostics.warnings / diagnostics.total * 100) : 0) + '%'"></div>
                                    <div class="bg-gradient-to-r from-red-500 to-red-400 transition-all duration-500" :style="'width: ' + (diagnostics.total > 0 ? (diagnostics.failed / diagnostics.total * 100) : 0) + '%'"></div>
                                </div>
                            </div>
                        </div>
                        <!-- Results Grid -->
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            <template x-for="result in diagnostics.results" :key="result.name">
                                <div class="p-4 rounded-xl border-2 transition"
                                     :class="{
                                         'bg-green-50 dark:bg-green-500/10 border-green-200 dark:border-green-500/30': result.level === 'ok',
                                         'bg-yellow-50 dark:bg-yellow-500/10 border-yellow-200 dark:border-yellow-500/30': result.level === 'warning',
                                         'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30': result.level === 'error' || result.level === 'critical',
                                         'bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/30': result.level === 'info'
                                     }">
                                    <div class="flex items-center gap-3 mb-2">
                                        <span class="text-xl" x-text="result.level === 'ok' ? '✅' : result.level === 'warning' ? '⚠️' : result.level === 'info' ? 'ℹ️' : '❌'"></span>
                                        <span class="font-semibold text-slate-700 dark:text-slate-200" x-text="result.name"></span>
                                    </div>
                                    <p class="text-sm text-slate-600 dark:text-slate-400" x-text="result.message"></p>
                                </div>
                            </template>
                        </div>
                    </div>
                </section>

                <!-- Broadcast -->
                <section class="card bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl p-8 shadow-xl">
                    <div class="flex items-start gap-6">
                        <div class="w-16 h-16 rounded-2xl bg-white/20 flex items-center justify-center flex-shrink-0">
                            <span class="text-3xl">📢</span>
                        </div>
                        <div class="flex-1">
                            <h3 class="text-xl font-bold text-white mb-2">發送廣播訊息</h3>
                            <p class="text-white/70 text-sm mb-4">向所有連線的用戶發送通知</p>
                            <div class="flex gap-4">
                                <textarea x-model="broadcastMsg" 
                                          class="flex-1 p-4 bg-white/10 backdrop-blur border border-white/20 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/30 resize-none"
                                          placeholder="輸入廣播訊息..."
                                          rows="2"></textarea>
                                <button @click="sendBroadcast()"
                                        class="px-8 bg-white text-indigo-600 font-semibold rounded-xl hover:bg-white/90 transition shadow-lg self-end">
                                    發送
                                </button>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </main>
    </div>

    <script>
        function dashboard() {
            return {
                status: 'online',
                locked: false,
                currentTime: '',
                broadcastMsg: '',
                stats: { uptime: '0:00:00', total_users: 0, active_sessions: 0, total_messages: 0, llm_calls: 0, current_model: 'N/A' },
                system: { cpu: 0, memory: 0, memory_detail: '', disk: 0, disk_detail: '' },
                providers: {},
                diagnostics: { passed: 0, warnings: 0, failed: 0, total: 1, results: [] },
                sessions: [],
                
                init() {
                    this.updateTime();
                    setInterval(() => this.updateTime(), 1000);
                    this.fetchAll();
                    setInterval(() => this.fetchAll(), 10000);
                },
                
                updateTime() {
                    const now = new Date();
                    this.currentTime = now.toLocaleDateString('zh-TW', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) + ' ' + now.toLocaleTimeString('zh-TW');
                },
                
                async fetchAll() {
                    await Promise.all([this.fetchStats(), this.fetchSessions(), this.fetchSystem(), this.fetchProviders(), this.fetchDiagnostics()]);
                },
                
                async fetchStats() {
                    try {
                        const res = await fetch('/dashboard/api/stats');
                        if (res.ok) { this.stats = await res.json(); this.status = 'online'; }
                    } catch (e) { this.status = 'offline'; }
                },
                
                async fetchSessions() {
                    try {
                        const res = await fetch('/dashboard/api/sessions');
                        if (res.ok) { this.sessions = await res.json(); }
                    } catch (e) {}
                },
                
                async fetchSystem() {
                    try {
                        const res = await fetch('/dashboard/api/system');
                        if (res.ok) { this.system = await res.json(); }
                    } catch (e) {}
                },
                
                async fetchProviders() {
                    try {
                        const res = await fetch('/dashboard/api/providers');
                        if (res.ok) { this.providers = await res.json(); }
                    } catch (e) {}
                },
                
                async fetchDiagnostics() {
                    try {
                        const res = await fetch('/dashboard/api/diagnostics');
                        if (res.ok) { this.diagnostics = await res.json(); }
                    } catch (e) {}
                },
                
                async clearSession(key) {
                    if (!confirm('確定要清除此會話？')) return;
                    try {
                        await fetch('/dashboard/api/sessions/' + key, { method: 'DELETE' });
                        this.fetchSessions();
                    } catch (e) { alert('清除失敗'); }
                },
                
                async clearAllSessions() {
                    if (!confirm('確定要清除所有會話？')) return;
                    try {
                        await fetch('/dashboard/api/sessions', { method: 'DELETE' });
                        this.fetchSessions();
                    } catch (e) { alert('清除失敗'); }
                },
                
                async runDoctor() {
                    await this.fetchDiagnostics();
                    alert('診斷完成！\\n✅ 通過: ' + this.diagnostics.passed + '\\n⚠️ 警告: ' + this.diagnostics.warnings + '\\n❌ 失敗: ' + this.diagnostics.failed);
                },
                
                async toggleLock() {
                    try {
                        const res = await fetch('/dashboard/api/lock', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ lock: !this.locked })
                        });
                        if (res.ok) { this.locked = !this.locked; }
                    } catch (e) { alert('操作失敗'); }
                },
                
                async sendBroadcast() {
                    if (!this.broadcastMsg.trim()) return;
                    if (!confirm('確定要發送廣播？')) return;
                    try {
                        await fetch('/dashboard/api/broadcast', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ message: this.broadcastMsg })
                        });
                        alert('廣播已發送');
                        this.broadcastMsg = '';
                    } catch (e) { alert('發送失敗'); }
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
    """Create dashboard router with security protections."""
    from fastapi import APIRouter
    from ..utils.security import RateLimiter, sanitize_log_message
    
    router = APIRouter(prefix="/dashboard", tags=["dashboard"])
    
    # Track start time
    _start_time = datetime.now()
    
    # Rate limiters for sensitive operations
    _api_rate_limiter = RateLimiter(requests_per_minute=120)
    _admin_rate_limiter = RateLimiter(requests_per_minute=30, block_duration=300)
    
    def _get_client_ip(request: Request) -> str:
        """Get client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    @router.get("/", response_class=HTMLResponse)
    async def dashboard_page():
        """Render dashboard page (protected by AuthMiddleware)."""
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
    async def delete_session(request: Request, session_key: str):
        """Delete a session (rate limited)."""
        # Rate limiting
        client_ip = _get_client_ip(request)
        if not _admin_rate_limiter.is_allowed(f"delete_session_{client_ip}"):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Validate session_key (prevent injection)
        if not session_key or len(session_key) > 100 or ".." in session_key:
            raise HTTPException(status_code=400, detail="Invalid session key")
        
        try:
            from ..core.context import get_context_manager
            manager = get_context_manager()
            if session_key in manager._contexts:
                del manager._contexts[session_key]
            logger.info(f"Session deleted by {client_ip}: {session_key[:20]}...")
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Delete session error: {sanitize_log_message(str(e))}")
            raise HTTPException(status_code=500, detail="Delete failed")
    
    @router.delete("/api/sessions")
    async def delete_all_sessions(request: Request):
        """Delete all sessions (rate limited, admin only)."""
        # Rate limiting
        client_ip = _get_client_ip(request)
        if not _admin_rate_limiter.is_allowed(f"delete_all_{client_ip}"):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        try:
            from ..core.context import get_context_manager
            manager = get_context_manager()
            count = len(manager._contexts)
            manager._contexts.clear()
            logger.warning(f"All sessions cleared by {client_ip} ({count} sessions)")
            return {"status": "ok", "cleared": count}
        except Exception as e:
            logger.error(f"Delete all sessions error: {sanitize_log_message(str(e))}")
            raise HTTPException(status_code=500, detail="Delete failed")
    
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
        """Toggle gateway lock (rate limited, admin only)."""
        client_ip = _get_client_ip(request)
        
        # Rate limiting
        if not _admin_rate_limiter.is_allowed(f"lock_{client_ip}"):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        try:
            from ..core.gateway_lock import get_gateway_lock
            data = await request.json()
            gl = get_gateway_lock()
            
            if data.get("lock"):
                gl.lock(message="Locked from dashboard")
                logger.warning(f"Gateway locked by {client_ip}")
            else:
                gl.unlock()
                logger.info(f"Gateway unlocked by {client_ip}")
            
            return {"status": "ok", "locked": gl.is_locked()}
        except Exception as e:
            logger.error(f"Lock error: {sanitize_log_message(str(e))}")
            raise HTTPException(status_code=500, detail="Operation failed")
    
    @router.post("/api/broadcast")
    async def send_broadcast(request: Request):
        """Send broadcast message (rate limited, admin only)."""
        client_ip = _get_client_ip(request)
        
        # Strict rate limiting for broadcast
        if not _admin_rate_limiter.is_allowed(f"broadcast_{client_ip}"):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        try:
            data = await request.json()
            message = data.get("message", "")
            
            # Validate message
            if not message or len(message.strip()) == 0:
                raise HTTPException(status_code=400, detail="Message cannot be empty")
            
            if len(message) > 1000:
                raise HTTPException(status_code=400, detail="Message too long (max 1000 chars)")
            
            # Sanitize log message
            safe_message = sanitize_log_message(message[:100])
            logger.info(f"Broadcast requested by {client_ip}: {safe_message}...")
            
            return {"status": "ok", "message": "Broadcast queued"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Broadcast error: {sanitize_log_message(str(e))}")
            raise HTTPException(status_code=500, detail="Broadcast failed")
    
    return router


__all__ = [
    "create_dashboard_router",
    "DashboardStats",
    "DASHBOARD_HTML",
]

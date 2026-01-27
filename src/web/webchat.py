"""
WebChat for CursorBot

Provides:
- Web-based chat interface
- Real-time messaging via WebSocket
- Session management
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..utils.logger import logger


# ============================================
# Models
# ============================================

class ChatMessage(BaseModel):
    """Chat message."""
    role: str  # user, assistant, system
    content: str
    timestamp: str = ""


class ChatSession(BaseModel):
    """Chat session."""
    session_id: str
    messages: list[ChatMessage] = []
    created_at: str = ""


# ============================================
# WebChat HTML
# ============================================

WEBCHAT_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CursorBot Chat</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .chat-container { height: calc(100vh - 180px); }
        .message-enter { animation: slideIn 0.3s ease; }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .typing-indicator span {
            animation: blink 1.4s infinite;
        }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes blink {
            0%, 60%, 100% { opacity: 0.3; }
            30% { opacity: 1; }
        }
        pre { white-space: pre-wrap; word-wrap: break-word; }
    </style>
</head>
<body class="bg-gray-50 min-h-screen flex flex-col" x-data="chatApp()">
    <!-- Header -->
    <header class="gradient-bg shadow-lg">
        <div class="max-w-4xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <span class="text-2xl">🤖</span>
                    <h1 class="text-xl font-bold text-white">CursorBot</h1>
                </div>
                <div class="flex items-center space-x-3">
                    <span class="text-white/70 text-sm" x-show="connected">● 已連線</span>
                    <span class="text-red-300 text-sm" x-show="!connected">○ 未連線</span>
                    <button @click="clearChat()" class="text-white/80 hover:text-white text-sm">
                        🗑️ 清除對話
                    </button>
                </div>
            </div>
        </div>
    </header>

    <!-- Chat Container -->
    <main class="flex-1 max-w-4xl w-full mx-auto p-4">
        <div class="bg-white rounded-2xl shadow-lg h-full flex flex-col overflow-hidden">
            <!-- Messages -->
            <div class="chat-container flex-1 overflow-y-auto p-6 space-y-4" id="messages">
                <!-- Welcome -->
                <div x-show="messages.length === 0" class="text-center py-12">
                    <span class="text-6xl mb-4 block">🤖</span>
                    <h2 class="text-xl font-semibold text-gray-700 mb-2">歡迎使用 CursorBot</h2>
                    <p class="text-gray-500">輸入訊息開始對話</p>
                </div>
                
                <!-- Messages -->
                <template x-for="(msg, index) in messages" :key="index">
                    <div class="message-enter" :class="msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'">
                        <div class="max-w-[80%] rounded-2xl px-4 py-3"
                             :class="msg.role === 'user' 
                                 ? 'bg-blue-500 text-white rounded-br-md' 
                                 : 'bg-gray-100 text-gray-800 rounded-bl-md'">
                            <div x-html="formatMessage(msg.content)"></div>
                            <div class="text-xs mt-1 opacity-60" x-text="msg.timestamp"></div>
                        </div>
                    </div>
                </template>
                
                <!-- Typing Indicator -->
                <div x-show="isTyping" class="flex justify-start">
                    <div class="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
                        <div class="typing-indicator flex space-x-1">
                            <span class="w-2 h-2 bg-gray-400 rounded-full"></span>
                            <span class="w-2 h-2 bg-gray-400 rounded-full"></span>
                            <span class="w-2 h-2 bg-gray-400 rounded-full"></span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Input -->
            <div class="p-4 border-t border-gray-200">
                <form @submit.prevent="sendMessage()" class="flex space-x-3">
                    <input type="text" 
                           x-model="input"
                           placeholder="輸入訊息..."
                           class="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                           :disabled="!connected || isTyping">
                    <button type="submit"
                            class="px-6 py-3 bg-blue-500 text-white rounded-xl font-medium hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
                            :disabled="!input.trim() || !connected || isTyping">
                        發送
                    </button>
                </form>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="py-3 text-center text-gray-400 text-sm">
        CursorBot WebChat v0.3
    </footer>

    <script>
        function chatApp() {
            return {
                input: '',
                messages: [],
                isTyping: false,
                connected: false,
                ws: null,
                sessionId: '',
                
                init() {
                    this.sessionId = localStorage.getItem('chatSessionId') || this.generateSessionId();
                    localStorage.setItem('chatSessionId', this.sessionId);
                    this.connect();
                    this.loadHistory();
                },
                
                generateSessionId() {
                    return 'web_' + Math.random().toString(36).substr(2, 9);
                },
                
                connect() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    this.ws = new WebSocket(`${protocol}//${window.location.host}/chat/ws/${this.sessionId}`);
                    
                    this.ws.onopen = () => {
                        this.connected = true;
                        console.log('WebSocket connected');
                    };
                    
                    this.ws.onclose = () => {
                        this.connected = false;
                        console.log('WebSocket disconnected');
                        setTimeout(() => this.connect(), 3000);
                    };
                    
                    this.ws.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    };
                },
                
                handleMessage(data) {
                    if (data.type === 'response') {
                        this.isTyping = false;
                        const content = data.content || '(無回應)';
                        this.addMessage('assistant', content);
                    } else if (data.type === 'typing') {
                        this.isTyping = true;
                    } else if (data.type === 'error') {
                        this.isTyping = false;
                        this.addMessage('assistant', `❌ 錯誤: ${data.content || '未知錯誤'}`);
                    }
                },
                
                sendMessage() {
                    if (!this.input.trim() || !this.connected) return;
                    
                    const content = this.input.trim();
                    this.input = '';
                    
                    this.addMessage('user', content);
                    this.isTyping = true;
                    
                    this.ws.send(JSON.stringify({
                        type: 'message',
                        content: content
                    }));
                    
                    this.scrollToBottom();
                },
                
                addMessage(role, content) {
                    const timestamp = new Date().toLocaleTimeString('zh-TW', { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                    });
                    
                    this.messages.push({ role, content, timestamp });
                    this.saveHistory();
                    
                    this.$nextTick(() => this.scrollToBottom());
                },
                
                formatMessage(content) {
                    // Simple markdown-like formatting
                    let html = content
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;')
                        .replace(/```([\\s\\S]*?)```/g, '<pre class="bg-gray-800 text-green-400 p-3 rounded-lg my-2 text-sm overflow-x-auto">$1</pre>')
                        .replace(/`([^`]+)`/g, '<code class="bg-gray-200 text-gray-800 px-1 rounded">$1</code>')
                        .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
                        .replace(/\\n/g, '<br>');
                    return html;
                },
                
                scrollToBottom() {
                    const container = document.getElementById('messages');
                    container.scrollTop = container.scrollHeight;
                },
                
                clearChat() {
                    if (!confirm('確定要清除所有對話？')) return;
                    this.messages = [];
                    this.saveHistory();
                },
                
                saveHistory() {
                    localStorage.setItem('chatHistory', JSON.stringify(this.messages.slice(-50)));
                },
                
                loadHistory() {
                    const saved = localStorage.getItem('chatHistory');
                    if (saved) {
                        try {
                            const parsed = JSON.parse(saved);
                            // Filter out invalid messages (undefined, null, or empty content)
                            this.messages = parsed.filter(msg => 
                                msg && msg.content && msg.content !== 'undefined' && msg.content.trim() !== ''
                            );
                        } catch (e) {
                            this.messages = [];
                        }
                    }
                },
                
                clearLocalStorage() {
                    localStorage.removeItem('chatHistory');
                    this.messages = [];
                }
            }
        }
    </script>
</body>
</html>
"""


# ============================================
# WebChat Manager
# ============================================

class WebChatManager:
    """Manages WebChat sessions and connections."""
    
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._sessions: dict[str, list[dict]] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Handle new connection."""
        await websocket.accept()
        self._connections[session_id] = websocket
        
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        
        logger.info(f"WebChat connected: {session_id}")
    
    def disconnect(self, session_id: str) -> None:
        """Handle disconnection."""
        self._connections.pop(session_id, None)
        logger.info(f"WebChat disconnected: {session_id}")
    
    async def send_message(self, session_id: str, msg_type: str, content: str) -> None:
        """Send message to client."""
        ws = self._connections.get(session_id)
        if ws:
            try:
                await ws.send_json({
                    "type": msg_type,
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.error(f"Send error: {e}")
    
    async def process_message(self, session_id: str, content: str) -> str:
        """Process incoming message and generate response."""
        # Store message
        self._sessions.setdefault(session_id, []).append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Send typing indicator
        await self.send_message(session_id, "typing", "")
        
        try:
            # Get LLM response
            from ..core.llm_providers import get_llm_manager
            from ..core.context import get_context_manager
            
            llm = get_llm_manager()
            ctx_manager = get_context_manager()
            
            # Get or create context
            ctx = ctx_manager.get_context(0, session_id)  # user_id=0 for web
            ctx.add_message("user", content)
            
            # Generate response
            response = await llm.generate(
                messages=ctx.get_messages_for_api(),
                system_prompt="You are CursorBot, a helpful AI assistant. Respond in the user's language.",
            )
            
            # Ensure response is not None or empty
            if not response:
                response = "抱歉，我無法生成回應。請確認 AI 提供者已正確設定。"
            
            # Store response
            ctx.add_message("assistant", response)
            self._sessions[session_id].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat(),
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Process error: {e}")
            error_msg = str(e)
            if "No LLM provider" in error_msg:
                return "❌ 尚未設定 AI 提供者。請在 .env 中設定 OPENAI_API_KEY、ANTHROPIC_API_KEY 或其他 AI API 金鑰。"
            elif "All LLM providers failed" in error_msg:
                return f"❌ 所有 AI 提供者都失敗了。請檢查 API 金鑰是否正確。\n\n詳細: {error_msg[:200]}"
            return f"❌ 處理訊息時發生錯誤: {error_msg}"
    
    def get_history(self, session_id: str) -> list[dict]:
        """Get session history."""
        return self._sessions.get(session_id, [])
    
    def clear_history(self, session_id: str) -> None:
        """Clear session history."""
        self._sessions[session_id] = []


# Global instance
_webchat_manager: Optional[WebChatManager] = None


def get_webchat_manager() -> WebChatManager:
    """Get WebChat manager instance."""
    global _webchat_manager
    if _webchat_manager is None:
        _webchat_manager = WebChatManager()
    return _webchat_manager


# ============================================
# WebChat Router
# ============================================

def create_webchat_router():
    """Create WebChat router."""
    router = APIRouter(prefix="/chat", tags=["webchat"])
    manager = get_webchat_manager()
    
    @router.get("/", response_class=HTMLResponse)
    async def webchat_page():
        """Render WebChat page."""
        return HTMLResponse(content=WEBCHAT_HTML)
    
    @router.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        """WebSocket endpoint for chat."""
        await manager.connect(session_id, websocket)
        
        try:
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "message":
                    content = data.get("content", "")
                    if content:
                        response = await manager.process_message(session_id, content)
                        await manager.send_message(session_id, "response", response)
        
        except WebSocketDisconnect:
            manager.disconnect(session_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(session_id)
    
    @router.get("/history/{session_id}")
    async def get_history(session_id: str):
        """Get chat history."""
        return manager.get_history(session_id)
    
    @router.delete("/history/{session_id}")
    async def clear_history(session_id: str):
        """Clear chat history."""
        manager.clear_history(session_id)
        return {"status": "ok"}
    
    return router


__all__ = [
    "create_webchat_router",
    "WebChatManager",
    "get_webchat_manager",
    "WEBCHAT_HTML",
]

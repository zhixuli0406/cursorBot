#!/usr/bin/env python3
"""
MCP Server for CursorBot
Allows Cursor IDE to receive questions from Telegram and send answers back

This server provides tools that Cursor Agent can use to:
1. Get pending questions from Telegram users
2. Answer questions (automatically sent back to Telegram)
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Data storage path
DATA_DIR = Path(__file__).parent.parent.parent / "data"
QUESTIONS_FILE = DATA_DIR / "pending_questions.json"
ANSWERS_FILE = DATA_DIR / "answers.json"


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not QUESTIONS_FILE.exists():
        QUESTIONS_FILE.write_text("[]")
    if not ANSWERS_FILE.exists():
        ANSWERS_FILE.write_text("[]")


def load_questions() -> list[dict]:
    """Load pending questions."""
    ensure_data_dir()
    try:
        return json.loads(QUESTIONS_FILE.read_text())
    except Exception:
        return []


def save_questions(questions: list[dict]):
    """Save questions to file."""
    ensure_data_dir()
    QUESTIONS_FILE.write_text(json.dumps(questions, ensure_ascii=False, indent=2))


def load_answers() -> list[dict]:
    """Load answers."""
    ensure_data_dir()
    try:
        return json.loads(ANSWERS_FILE.read_text())
    except Exception:
        return []


def save_answers(answers: list[dict]):
    """Save answers to file."""
    ensure_data_dir()
    ANSWERS_FILE.write_text(json.dumps(answers, ensure_ascii=False, indent=2))


def add_question(question_id: str, user_id: int, username: str, question: str) -> dict:
    """Add a new question from Telegram."""
    questions = load_questions()
    
    q = {
        "id": question_id,
        "user_id": user_id,
        "username": username,
        "question": question,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    
    questions.append(q)
    save_questions(questions)
    return q


def get_pending_questions() -> list[dict]:
    """Get all pending questions."""
    questions = load_questions()
    return [q for q in questions if q.get("status") == "pending"]


def answer_question(question_id: str, answer: str) -> bool:
    """Answer a question."""
    questions = load_questions()
    
    for q in questions:
        if q["id"] == question_id:
            q["status"] = "answered"
            q["answered_at"] = datetime.now().isoformat()
            break
    
    save_questions(questions)
    
    # Save answer
    answers = load_answers()
    answers.append({
        "question_id": question_id,
        "answer": answer,
        "created_at": datetime.now().isoformat(),
    })
    save_answers(answers)
    
    return True


def get_new_answers() -> list[dict]:
    """Get answers that haven't been sent to Telegram yet."""
    answers = load_answers()
    # Return answers and clear them
    save_answers([])
    return answers


# ============================================
# MCP Protocol Implementation
# ============================================

class MCPServer:
    """
    MCP Server using stdio transport.
    Implements the Model Context Protocol for Cursor IDE.
    """

    def __init__(self):
        self.tools = {
            "get_telegram_questions": {
                "description": "獲取來自 Telegram 的待處理問題。返回所有 status 為 pending 的問題列表。請定期呼叫此工具檢查新問題。",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            "answer_telegram_question": {
                "description": "回答一個 Telegram 問題。提供問題 ID 和你的回答，答案會自動發送回 Telegram。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question_id": {
                            "type": "string",
                            "description": "問題的 ID",
                        },
                        "answer": {
                            "type": "string",
                            "description": "你的回答內容，可以包含 markdown 格式",
                        },
                    },
                    "required": ["question_id", "answer"],
                },
            },
        }

    async def handle_request(self, request: dict) -> dict:
        """Handle an MCP request."""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return self._response(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "cursorbot",
                    "version": "1.0.0",
                },
            })

        elif method == "tools/list":
            tools_list = []
            for name, info in self.tools.items():
                tools_list.append({
                    "name": name,
                    "description": info["description"],
                    "inputSchema": info["inputSchema"],
                })
            return self._response(req_id, {"tools": tools_list})

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            result = await self._call_tool(tool_name, arguments)
            return self._response(req_id, {
                "content": [{"type": "text", "text": result}],
            })

        elif method == "notifications/initialized":
            # No response needed for notifications
            return None

        else:
            return self._error(req_id, -32601, f"Method not found: {method}")

    async def _call_tool(self, name: str, arguments: dict) -> str:
        """Execute a tool and return the result."""
        if name == "get_telegram_questions":
            questions = get_pending_questions()
            if not questions:
                return "目前沒有待處理的問題。"
            
            result = f"找到 {len(questions)} 個待處理問題：\n\n"
            for q in questions:
                result += f"---\n"
                result += f"ID: {q['id']}\n"
                result += f"用戶: {q['username']} (ID: {q['user_id']})\n"
                result += f"時間: {q['created_at']}\n"
                result += f"問題: {q['question']}\n\n"
            
            result += "請使用 answer_telegram_question 工具回答問題。"
            return result

        elif name == "answer_telegram_question":
            question_id = arguments.get("question_id")
            answer = arguments.get("answer")
            
            if not question_id or not answer:
                return "錯誤：需要提供 question_id 和 answer"
            
            success = answer_question(question_id, answer)
            if success:
                return f"✅ 已回答問題 {question_id}，答案將發送到 Telegram。"
            else:
                return f"❌ 找不到問題 {question_id}"

        else:
            return f"未知工具: {name}"

    def _response(self, req_id: Any, result: dict) -> dict:
        """Create a success response."""
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        }

    def _error(self, req_id: Any, code: int, message: str) -> dict:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }

    async def run_stdio(self):
        """Run the server using stdio transport."""
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue

                request = json.loads(line)
                response = await self.handle_request(request)
                
                if response:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

            except json.JSONDecodeError as e:
                sys.stderr.write(f"JSON decode error: {e}\n")
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")


async def main():
    """Main entry point."""
    server = MCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())

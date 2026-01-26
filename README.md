# CursorBot - Telegram 遠端操控 Cursor Agent

透過 Telegram Bot 遠端操控 Cursor AI Agent，實現隨時隨地的程式碼開發與專案管理。

## 系統架構

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Telegram      │────▶│   CursorBot     │────▶│  Cursor Agent   │
│   (使用者)       │◀────│   Server        │◀────│  (本地 IDE)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │    HTTP/Webhook       │     WebSocket/MCP     │
        │                       │                       │
   使用者發送指令          解析並轉發指令           執行程式碼操作
   接收執行結果            回傳執行狀態             返回操作結果
```

## 核心功能

### 1. 基礎操控指令
- `/start` - 啟動 Bot 並進行身份驗證
- `/status` - 查看 Cursor Agent 連線狀態
- `/help` - 顯示所有可用指令

### 2. Cursor Cloud Agent
- `/ask <問題>` - 詢問 Cursor AI（使用 Cloud Agent）
- `/repo <github_url>` - 設定 GitHub 倉庫
- `/agents` - 列出所有 Agents
- `/agent <id>` - 查看 Agent 狀態
- `/models` - 列出可用模型
- `/cursor` - 查看 Cursor API 狀態
- 直接發送訊息也可以對話！

### 3. 檔案操作
- `/file read <路徑>` - 讀取檔案內容
- `/file list <目錄>` - 列出目錄檔案
- `/write <路徑>` - 建立或覆寫檔案
- `/edit <檔案> <舊文字> -> <新文字>` - 編輯檔案
- `/delete <路徑>` - 刪除檔案
- `/undo` - 復原上一次編輯
- `/history` - 顯示編輯歷史

### 4. 終端機操作
- `/run <命令>` - 執行命令並等待結果
- `/run_bg <命令>` - 背景執行命令
- `/jobs` - 查看執行中的命令
- `/kill <ID>` - 停止執行中的命令

### 5. 任務管理
- `/tasks` - 查看您的任務列表
- `/cancel <ID>` - 取消任務
- `/queue` - 查看任務佇列狀態

### 6. 工作區管理
- `/workspace` - 顯示目前工作區資訊
- `/workspace list` - 列出所有可用工作區（含互動按鈕）
- `/cd <名稱>` - 快速切換工作區
- `/pwd` - 顯示目前工作路徑

### 7. 搜尋與專案
- `/search <關鍵字>` - 搜尋程式碼庫
- `/project list` - 列出當前工作區的專案
- `/project switch <名稱>` - 切換專案

### 8. 安全功能
- 白名單機制（僅允許授權用戶）
- 操作日誌記錄
- 危險命令封鎖
- 速率限制（每分鐘請求數）
- 任務佇列與用戶隔離

## 目錄結構

```
cursorBot/
├── README.md                 # 專案說明文件
├── requirements.txt          # Python 依賴套件
├── .env.example             # 環境變數範例
├── .gitignore               # Git 忽略檔案
│
├── src/
│   ├── __init__.py
│   ├── main.py              # 主程式入口
│   │
│   ├── bot/                 # Telegram Bot 模組
│   │   ├── __init__.py
│   │   ├── telegram_bot.py  # Bot 主要邏輯
│   │   ├── handlers.py      # 指令處理器
│   │   └── keyboards.py     # 自訂鍵盤介面
│   │
│   ├── cursor/              # Cursor Agent 通訊模組
│   │   ├── __init__.py
│   │   ├── agent.py         # Agent 連線管理
│   │   ├── commands.py      # Cursor 指令封裝
│   │   └── mcp_client.py    # MCP 協議客戶端
│   │
│   ├── server/              # API Server 模組
│   │   ├── __init__.py
│   │   ├── api.py           # FastAPI 路由
│   │   └── websocket.py     # WebSocket 處理
│   │
│   └── utils/               # 工具模組
│       ├── __init__.py
│       ├── config.py        # 配置管理
│       ├── logger.py        # 日誌系統
│       └── auth.py          # 身份驗證
│
└── tests/                   # 測試檔案
    ├── __init__.py
    ├── test_bot.py
    └── test_cursor.py
```

## 技術選型

| 元件 | 技術 | 說明 |
|------|------|------|
| Telegram Bot | python-telegram-bot | 成熟穩定的 Telegram Bot 框架 |
| Web Server | FastAPI | 高效能異步 API 框架 |
| Cursor 通訊 | WebSocket + MCP | 與 Cursor Agent 雙向通訊 |
| 任務佇列 | asyncio | 異步任務處理 |
| 資料儲存 | SQLite/Redis | 輕量級資料持久化 |

## 安裝與設定

### 1. 環境需求
- Python 3.10+
- Cursor IDE（需運行中）
- Telegram Bot Token

### 2. 安裝步驟

```bash
# 複製專案
cd /Users/lizhixu/Project/cursorBot

# 建立虛擬環境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入您的設定
```

### 3. 環境變數設定

```env
# Telegram Bot 設定
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USERS=123456789,987654321

# Cursor Agent 設定
CURSOR_WORKSPACE_PATH=/path/to/your/workspace
CURSOR_MCP_PORT=3000

# Server 設定
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false

# 安全設定
SECRET_KEY=your_secret_key_here
```

### 4. 啟動服務

```bash
# 啟動主服務
python -m src.main

# 或使用 uvicorn（支援熱重載）
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 使用指南

### 建立 Telegram Bot

1. 在 Telegram 中搜尋 `@BotFather`
2. 發送 `/newbot` 建立新 Bot
3. 依照指示設定 Bot 名稱
4. 取得 Bot Token 並填入 `.env`

### 首次使用

1. 啟動 CursorBot Server
2. 確保 Cursor IDE 正在運行
3. 在 Telegram 中搜尋您的 Bot
4. 發送 `/start` 開始使用

### 指令範例

```
# 詢問 Cursor Agent
/ask 如何在 Python 中實作單例模式？

# 執行程式碼操作
/code 建立一個 FastAPI 的 hello world

# 讀取檔案
/file read src/main.py

# 搜尋程式碼
/search def main

# 編輯檔案
/edit main.py print("old") -> print("new")

# 建立新檔案
/write hello.py
print("Hello World")

# 執行終端命令
/run python --version

# 背景執行
/run_bg npm run dev

# 查看執行中的任務
/jobs
```

## 開發計劃

### Phase 1: 基礎架構 ✅
- [x] 專案結構規劃
- [x] Telegram Bot 基礎功能
- [x] 配置管理系統

### Phase 2: 核心功能 ✅
- [x] Cursor Agent 連線
- [x] MCP 通訊協議實作
- [x] 基礎指令實作

### Phase 3: 進階功能 ✅
- [x] 檔案編輯操作（建立、編輯、刪除、復原）
- [x] 終端機執行（前景/背景）
- [x] 程式碼搜尋
- [x] 多專案切換

### Phase 4: 安全與優化 ✅
- [x] 完整身份驗證與白名單機制
- [x] 多用戶支援與隔離
- [x] 任務佇列與排隊機制
- [x] 操作日誌與歷史記錄
- [x] 速率限制

## 授權條款

MIT License

## 貢獻指南

歡迎提交 Issue 和 Pull Request！

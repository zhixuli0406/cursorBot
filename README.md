# CursorBot

透過 Telegram 遠端控制 Cursor IDE Agent。

## 運作模式

### 模式一：Background Agent（推薦）

```
Telegram → CursorBot → Cursor Cloud Agent → 自動執行 → 回傳結果
```

**完全遠端操作，無需開啟 IDE！**

1. 你在 Telegram 發送問題
2. CursorBot 呼叫 Cursor Background Agent API
3. Cursor 雲端 Agent 自動執行任務
4. 完成後自動回傳結果到 Telegram

### 模式二：MCP Server（備用）

```
Telegram → CursorBot → MCP Server ← Cursor IDE（手動）
```

1. 你在 Telegram 發送問題
2. CursorBot 將問題存入佇列
3. 在 Cursor IDE 中手動呼叫 MCP 工具
4. 使用 `/check` 獲取回覆

## 快速開始

### 1. 安裝依賴

```bash
cd cursorBot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp env.example .env
```

編輯 `.env`：

```env
# 必填
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USERS=your_user_id
CURSOR_WORKSPACE_PATH=/path/to/your/projects

# Background Agent（推薦啟用）
BACKGROUND_AGENT_ENABLED=true
CURSOR_API_KEY=your_api_key_here

# 可選：指定 GitHub 倉庫
CURSOR_GITHUB_REPO=https://github.com/your-username/your-repo
```

### 3. 取得 Cursor API Key

要啟用 Background Agent 模式，需要取得 Cursor API Key：

1. 前往 [Cursor Dashboard](https://cursor.com/dashboard?tab=background-agents)
2. 登入你的 Cursor 帳號
3. 點擊 **Background Agents** 標籤
4. 建立或複製你的 API Key
5. 將值貼到 `.env` 的 `CURSOR_API_KEY`

> ⚠️ 需要 Cursor Pro 訂閱才能使用 Background Agent

### 4. 設定 Cursor IDE（MCP 模式，可選）

在 Cursor 設定中加入 MCP Server。

建立或編輯 `~/.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "cursorbot": {
      "command": "python",
      "args": ["-m", "src.cursor.mcp_server"],
      "cwd": "/Users/lizhixu/Project/cursorBot"
    }
  }
}
```

> ⚠️ 請將 `cwd` 路徑改為你的 CursorBot 安裝路徑

### 4. 啟動服務

```bash
python -m src.main
```

### 5. 重啟 Cursor IDE

重啟後，Cursor 會載入 MCP Server，你就可以在 Cursor 中使用以下工具：

- `get_telegram_questions` - 獲取 Telegram 待處理問題
- `answer_telegram_question` - 回答問題（自動發送到 Telegram）

## 使用流程

### 在 Telegram

```
/ask 如何實作快速排序？
→ ✅ 問題已發送到 Cursor IDE (ID: abc12345)

/check
→ 🤖 Cursor 回覆: ...
```

### 在 Cursor IDE

在 Cursor 中對 Agent 說：

```
請檢查並回答 Telegram 的問題
```

或直接呼叫 MCP 工具：

```
使用 get_telegram_questions 工具獲取問題
```

## 指令說明

### 基礎指令

| 指令 | 說明 |
|------|------|
| `/start` | 啟動 Bot |
| `/help` | 顯示說明 |
| `/status` | 系統狀態 |

### AI 對話（Background Agent）

| 指令 | 說明 |
|------|------|
| `/ask <問題>` | 發送問題給 AI Agent（自動執行） |
| `/repo <owner/repo>` | 切換 GitHub 倉庫 |
| `/repos` | 查看帳號中所有的 GitHub 倉庫 |
| `/tasks` | 查看我的任務列表 |
| `/result <ID>` | 查看任務結果 |
| `/cancel_task <ID>` | 取消執行中的任務 |

**倉庫切換範例：**
```
/repo lizhixu/cursorBot
/repo https://github.com/facebook/react
```

### MCP 模式（需 IDE）

| 指令 | 說明 |
|------|------|
| `/check` | 檢查 Cursor IDE 回覆 |
| `/pending` | 查看待處理問題 |
| `/code <指令>` | 發送程式碼指令 |

### 檔案操作

| 指令 | 說明 |
|------|------|
| `/file read <路徑>` | 讀取檔案 |
| `/file list <目錄>` | 列出檔案 |
| `/write <路徑>` | 建立檔案 |
| `/edit <檔案>` | 編輯檔案 |
| `/delete <路徑>` | 刪除檔案 |

### 終端執行

| 指令 | 說明 |
|------|------|
| `/run <命令>` | 執行命令 |
| `/run_bg <命令>` | 背景執行 |
| `/jobs` | 查看執行中的命令 |
| `/kill <ID>` | 停止命令 |

### 工作區管理

| 指令 | 說明 |
|------|------|
| `/workspace` | 顯示工作區 |
| `/workspace list` | 列出所有工作區 |
| `/cd <名稱>` | 切換工作區 |
| `/search <關鍵字>` | 搜尋程式碼 |

## 專案結構

```
cursorBot/
├── src/
│   ├── bot/               # Telegram Bot
│   │   ├── handlers.py
│   │   └── handlers_extended.py
│   ├── cursor/            # Cursor 整合
│   │   ├── agent.py       # 工作區管理
│   │   ├── mcp_server.py  # MCP Server
│   │   ├── file_operations.py
│   │   └── terminal.py
│   ├── server/            # API Server
│   └── utils/             # 工具模組
├── data/                  # 問題與回答儲存
├── cursor_mcp_config.json # MCP 設定範例
└── README.md
```

## 注意事項

### Background Agent 模式

1. **需要 Cursor Pro** - Background Agent 使用 Max Mode，需要訂閱
2. **費用較高** - Background Agent 每次任務都會消耗額度
3. **API Key** - 從 Cursor Dashboard 取得，不會過期
4. **完全遠端** - 不需要開啟 Cursor IDE
5. **GitHub 整合** - 可以指定 GitHub 倉庫進行操作

### MCP 模式

1. **需要 Cursor Pro** - MCP 功能需要 Cursor Pro 訂閱
2. **需要重啟 Cursor** - 修改 `mcp.json` 後需要重啟 Cursor
3. **需要 IDE** - 必須在 Cursor IDE 中手動處理問題

### 通用

1. **本地運作** - 問題和回答存在本地 `data/` 目錄
2. **安全性** - 只有 `TELEGRAM_ALLOWED_USERS` 中的用戶可以使用

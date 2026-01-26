# CursorBot

透過 Telegram 遠端控制 Cursor Background Agent。

## 運作原理

```
Telegram → CursorBot → Cursor Background Agent API → 自動執行 → 回傳結果
```

**完全遠端操作，無需開啟 IDE！**

1. 你在 Telegram 發送問題
2. CursorBot 呼叫 Cursor Background Agent API
3. Cursor 雲端 Agent 自動執行任務
4. 完成後自動回傳結果到 Telegram

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
# 必填 - Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USERS=your_user_id

# 必填 - Background Agent
BACKGROUND_AGENT_ENABLED=true
CURSOR_API_KEY=your_api_key_here

# 可選 - 預設 GitHub 倉庫
CURSOR_GITHUB_REPO=https://github.com/your-username/your-repo

# 可選 - 工作區路徑
CURSOR_WORKSPACE_PATH=/path/to/your/projects
```

### 3. 取得 Cursor API Key

1. 前往 [Cursor Dashboard](https://cursor.com/dashboard?tab=background-agents)
2. 登入你的 Cursor 帳號
3. 點擊 **Background Agents** 標籤
4. 建立或複製你的 API Key
5. 將值貼到 `.env` 的 `CURSOR_API_KEY`

> ⚠️ 需要 Cursor Pro 訂閱才能使用 Background Agent

### 4. 啟動服務

```bash
./run.sh
# 或
python -m src.main
```

## 使用流程

### 設定倉庫

```
/repo lizhixu/my-project
→ ✅ 已切換倉庫: my-project
```

### 發送問題

```
/ask 幫我實作一個快速排序函數
→ 🚀 正在啟動 Background Agent...
→ ✅ 任務已建立
→ ⏳ 正在執行中...
```

### 查看結果

```
/tasks
→ 📋 我的任務
→ 🔄 執行中 (1)
→ • abc12345: 幫我實作一個快速排序函數...

/result abc12345
→ 📋 任務詳情
→ ✅ 狀態: completed
→ 📝 結果: ...
```

## 指令說明

### 基礎指令

| 指令 | 說明 |
|------|------|
| `/start` | 啟動 Bot |
| `/help` | 顯示說明 |
| `/status` | 系統狀態 |

### AI 對話

| 指令 | 說明 |
|------|------|
| `/ask <問題>` | 發送問題給 AI Agent |
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
│   ├── bot/                  # Telegram Bot
│   │   ├── handlers.py       # 指令處理
│   │   └── handlers_extended.py
│   ├── cursor/               # Cursor 整合
│   │   ├── agent.py          # 工作區管理
│   │   ├── background_agent.py  # Background Agent API
│   │   ├── file_operations.py
│   │   └── terminal.py
│   ├── server/               # API Server
│   └── utils/                # 工具模組
├── data/                     # 任務資料儲存
└── README.md
```

## 注意事項

1. **需要 Cursor Pro** - Background Agent 使用 Max Mode，需要訂閱
2. **費用較高** - Background Agent 每次任務都會消耗額度
3. **API Key** - 從 Cursor Dashboard 取得，不會過期
4. **完全遠端** - 不需要開啟 Cursor IDE
5. **GitHub 整合** - 必須指定 GitHub 倉庫才能使用
6. **安全性** - 只有 `TELEGRAM_ALLOWED_USERS` 中的用戶可以使用

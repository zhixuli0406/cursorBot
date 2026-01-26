# CursorBot

透過 Telegram 和 Discord 遠端控制 Cursor Background Agent。

靈感來自 [cursor-telegram-bot](https://github.com/Hormold/cursor-telegram-bot) 和 [ClawdBot](https://clawd.bot/)。

## 特點

### 多平台支援
- **Telegram** - 完整的 Telegram Bot 支援
- **Discord** - 完整的 Discord Bot 支援（斜線指令、按鈕）
- **統一介面** - 兩個平台使用相同的功能

### 核心功能
- **完全遠端** - 無需開啟 IDE，雲端執行
- **互動式按鈕** - 直覺的按鈕介面
- **語音訊息** - 發送語音自動轉錄為任務
- **圖片支援** - 發送圖片加入任務描述
- **即時通知** - 任務完成自動推送

### 進階功能（對標 ClawdBot）
- **記憶系統** - 記住用戶偏好和對話歷史
- **技能系統** - 可擴展的技能（翻譯、摘要、計算機、提醒）
- **對話上下文** - 智慧追蹤多輪對話
- **審批系統** - 敏感操作需要確認
- **排程任務** - 定時執行任務
- **Webhook** - 支援 GitHub/GitLab 事件觸發
- **Agent Loop** - 自主代理執行循環
- **Browser 工具** - 網頁自動化和截圖
- **代理工具** - 檔案操作、命令執行、網頁抓取

## 運作原理

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Telegram   │────▶│             │     │             │
│  Discord    │────▶│  CursorBot  │────▶│ Cursor API  │
│  (你)       │◀────│  (Bot)      │◀────│ (雲端 Agent)│
└─────────────┘     └─────────────┘     └─────────────┘
```

1. 你在 Telegram 或 Discord 發送問題
2. CursorBot 呼叫 Cursor Background Agent API
3. Cursor 雲端 Agent 自動執行任務
4. 完成後自動回傳結果

## 快速開始

### 方式一：Docker（推薦）

最簡單的方式，無需安裝 Python 或其他依賴。

#### 1. 安裝 Docker

- **Windows / macOS**: 下載 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux**: 參考 [Docker 官方文件](https://docs.docker.com/engine/install/)

#### 2. 設定環境變數

```bash
cp env.example .env
```

編輯 `.env` 填入你的設定（參考下方說明）。

#### 3. 啟動服務

**Windows:**
```cmd
docker-start.bat
```

**macOS / Linux:**
```bash
./docker-start.sh
```

**或使用 Docker Compose:**
```bash
docker compose up -d --build
```

#### Docker 常用指令

| 指令 | 說明 |
|------|------|
| `docker compose up -d` | 啟動服務（背景執行） |
| `docker compose down` | 停止服務 |
| `docker compose logs -f` | 查看即時日誌 |
| `docker compose restart` | 重啟服務 |
| `docker compose build --no-cache` | 重新建置映像 |

---

### 方式二：本地安裝

#### 1. 環境需求

- **Python 3.10 - 3.12**（不支援 3.13+）
- Windows / macOS / Linux

> ⚠️ **Windows 用戶注意**: 啟動腳本會自動檢測 Python 版本，若版本過新（3.13+）會自動安裝 Python 3.12。

#### 2. 安裝依賴

**自動安裝（推薦）：**

Windows 啟動腳本會自動：
- 檢測並安裝 Python 3.12（如果需要）
- 建立虛擬環境
- 安裝所有依賴
- 安裝 Playwright 瀏覽器

```cmd
# Windows CMD
start.bat

# Windows PowerShell
.\start.ps1
```

**手動安裝：**

```bash
cd cursorBot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium  # 安裝瀏覽器（可選）
```

#### 3. 設定環境變數

```bash
cp env.example .env
```

編輯 `.env`：

```env
# === Telegram 設定 ===
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USERS=your_user_id

# === Discord 設定（可選）===
DISCORD_ENABLED=true
DISCORD_BOT_TOKEN=your_discord_token
DISCORD_ALLOWED_GUILDS=123456789
DISCORD_ALLOWED_USERS=987654321

# === Background Agent 設定 ===
BACKGROUND_AGENT_ENABLED=true
CURSOR_API_KEY=your_api_key_here

# === 可選設定 ===
CURSOR_GITHUB_REPO=https://github.com/your-username/your-repo
CURSOR_WORKSPACE_PATH=/path/to/your/projects
```

#### 4. 取得 Cursor API Key

1. 前往 [Cursor Dashboard](https://cursor.com/dashboard?tab=background-agents)
2. 登入你的 Cursor 帳號
3. 點擊 **Background Agents** 標籤
4. 建立或複製你的 API Key
5. 將值貼到 `.env` 的 `CURSOR_API_KEY`

> ⚠️ 需要 Cursor Pro 訂閱才能使用 Background Agent

#### 5. 啟動服務

**Windows (CMD):**
```cmd
start.bat
```

**Windows (PowerShell):**
```powershell
.\start.ps1
```

**macOS / Linux:**
```bash
./start.sh
```

**手動啟動:**
```bash
python -m src.main
```

---

### Windows 啟動腳本功能

`start.bat` 和 `start.ps1` 提供以下自動化功能：

| 功能 | 說明 |
|------|------|
| Python 版本檢測 | 自動檢測 Python 版本，若 3.13+ 則安裝 3.12 |
| 自動安裝 Python | 透過 winget 或下載安裝程式自動安裝 |
| 虛擬環境管理 | 自動建立和啟用 venv |
| 依賴安裝 | 自動安裝所有 requirements |
| Playwright 安裝 | 自動安裝瀏覽器（用於網頁自動化） |
| 環境設定 | 自動複製 env.example 並提示編輯 |

## 使用流程

### 1. 選擇倉庫

```
/repo lizhixu/my-project
→ ✅ 已切換倉庫: my-project
   [🔗 在 GitHub 開啟] [💬 發送任務]
```

或點擊「選擇倉庫」按鈕從帳號中選擇。

### 2. 發送任務

**文字訊息:**
```
幫我實作一個快速排序函數
→ 🚀 正在啟動 Background Agent...
→ ✅ 任務已建立
   [🔗 在 Cursor 開啟] [🔄 查看狀態] [❌ 取消]
```

**語音訊息:**
```
🎤 [語音: "新增登入功能"]
→ 🎤 正在轉錄語音訊息...
→ ✅ 任務已建立
```

**圖片 + 文字:**
```
📸 [發送 UI 設計圖]
→ 📸 圖片已儲存（3 分鐘內有效）

根據這張設計圖建立 React 元件
→ ✅ 任務已建立（1 張圖片附件）
```

### 3. 查看結果

任務完成時會自動推送通知：
```
✅ 任務完成

🆔 abc12345
📝 結果: ...

[🔗 在 Cursor 開啟] [💬 追問] [📋 複製結果]
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

### 記憶與技能（對標 ClawBot）

| 指令 | 說明 |
|------|------|
| `/memory` | 查看記憶 |
| `/memory add <key> <value>` | 新增記憶 |
| `/memory get <key>` | 取得記憶 |
| `/memory del <key>` | 刪除記憶 |
| `/skills` | 查看可用技能 |
| `/translate <lang> <text>` | 翻譯 |
| `/calc <expression>` | 計算 |
| `/remind <time> <message>` | 設定提醒 |

### 系統管理

| 指令 | 說明 |
|------|------|
| `/stats` | 使用統計 |
| `/settings` | 用戶設定 |
| `/schedule` | 查看排程 |
| `/clear` | 清除對話上下文 |

## 專案結構

```
cursorBot/
├── src/
│   ├── bot/                     # Telegram Bot
│   │   ├── handlers.py          # 基礎指令處理
│   │   ├── handlers_extended.py # 檔案/終端處理
│   │   ├── callbacks.py         # 按鈕回調處理
│   │   ├── media_handlers.py    # 語音/圖片處理
│   │   ├── core_handlers.py     # 核心功能處理
│   │   └── keyboards.py         # 按鈕佈局
│   ├── channels/                # 多平台支援
│   │   ├── base.py              # Channel 抽象層
│   │   ├── manager.py           # Channel 管理器
│   │   ├── discord_channel.py   # Discord 實現
│   │   └── discord_handlers.py  # Discord 處理器
│   ├── cursor/                  # Cursor 整合
│   │   ├── agent.py             # 工作區管理
│   │   ├── background_agent.py  # Background Agent API
│   │   ├── file_operations.py
│   │   └── terminal.py
│   ├── core/                    # 核心功能（對標 ClawdBot）
│   │   ├── memory.py            # 記憶系統
│   │   ├── skills.py            # 技能系統
│   │   ├── context.py           # 對話上下文
│   │   ├── approvals.py         # 審批系統
│   │   ├── scheduler.py         # 排程任務
│   │   ├── webhooks.py          # Webhook 處理
│   │   ├── tools.py             # 代理工具
│   │   ├── browser.py           # 瀏覽器自動化
│   │   └── agent_loop.py        # Agent 執行循環
│   ├── server/                  # API Server
│   └── utils/                   # 工具模組
├── data/                        # 資料儲存
├── skills/                      # 自訂技能（可選）
├── Dockerfile                   # Docker 映像定義
├── docker-compose.yml           # Docker Compose 設定
├── docker-start.bat             # Windows Docker 啟動腳本
├── docker-start.sh              # Linux/macOS Docker 啟動腳本
├── start.bat                    # Windows 本地啟動腳本
├── start.ps1                    # PowerShell 本地啟動腳本
├── start.sh                     # Linux/macOS 本地啟動腳本
├── env.example                  # 環境變數範例
├── requirements.txt             # Python 依賴
└── README.md
```

## Discord 設定

### 1. 建立 Discord Bot

1. 前往 [Discord Developer Portal](https://discord.com/developers/applications)
2. 點擊 **New Application**
3. 進入 **Bot** 標籤，點擊 **Add Bot**
4. 複製 **Token**
5. 啟用 **Message Content Intent**

### 2. 邀請 Bot 到伺服器

使用此 URL 邀請（替換 CLIENT_ID）：
```
https://discord.com/api/oauth2/authorize?client_id=CLIENT_ID&permissions=274877975552&scope=bot%20applications.commands
```

### 3. 設定環境變數

```env
DISCORD_ENABLED=true
DISCORD_BOT_TOKEN=your_token_here
DISCORD_ALLOWED_GUILDS=your_guild_id
```

### 4. Discord 指令

| 指令 | 說明 |
|------|------|
| `/start` | 開始使用 |
| `/help` | 顯示說明 |
| `/status` | 系統狀態 |
| `/ask <問題>` | 發送問題給 AI |
| `/repo <owner/repo>` | 設定倉庫 |
| `/tasks` | 查看任務 |
| `/memory` | 記憶管理 |
| `/skills` | 查看技能 |

## Docker 終端機功能

當 CursorBot 運行在 Docker 容器內時，`/run` 等終端機指令會在**容器內**執行。

### 設定工作目錄

在 `.env` 文件中設定 `CURSOR_WORKSPACE_PATH`，Docker 會自動掛載該目錄：

```env
# Windows
CURSOR_WORKSPACE_PATH=C:/Users/YourName/Projects

# macOS
CURSOR_WORKSPACE_PATH=/Users/yourname/projects

# Linux
CURSOR_WORKSPACE_PATH=/home/yourname/projects
```

`docker-compose.yml` 會自動讀取這個路徑並掛載到容器的 `/workspace` 目錄。

### 使用方式

掛載後，可以在 Bot 中這樣使用：

```
/run ls /workspace
/run cat /workspace/myproject/README.md
/cd /workspace/myproject
/run npm install
```

### 進入容器終端

如需直接進入容器操作：

```bash
docker exec -it cursorbot /bin/bash
```

### 容器內可用工具

Docker 映像已包含：
- Python 3.12
- pip
- Playwright（Chromium）
- curl
- 基本 Linux 工具

### 安全注意事項

- 掛載的目錄在容器內可完全存取
- 避免掛載系統敏感目錄（如 `/`, `C:\Windows`）
- 建議只掛載專案工作目錄

---

## 疑難排解

### Docker 相關

| 問題 | 解決方案 |
|------|----------|
| `load metadata` 錯誤 | 執行 `docker logout` 然後 `docker login` |
| 憑證錯誤 | 清除 Windows 憑證管理員中的 docker 憑證 |
| 映像拉取失敗 | 檢查網路連線，或嘗試使用 VPN |
| 容器啟動失敗 | 執行 `docker compose logs` 查看錯誤訊息 |
| 終端指令找不到檔案 | 檢查 `docker-compose.yml` 的 volumes 掛載設定 |

### Windows 本地安裝

| 問題 | 解決方案 |
|------|----------|
| Python 3.13+ 不相容 | 啟動腳本會自動安裝 Python 3.12 |
| `pydantic-core` 編譯失敗 | 安裝 [Rust](https://rustup.rs) 或使用 Python 3.12 |
| 腳本閃退 | 執行 `debug.bat` 診斷問題 |
| pip 安裝失敗 | 確保網路連線正常，或使用國內鏡像 |

### 常見錯誤

```
error: linker `link.exe` not found
```
→ 安裝 [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 或使用 Docker

```
Pre-built packages not available
```
→ Python 版本過新，請使用 Python 3.11 或 3.12

## 注意事項

1. **需要 Cursor Pro** - Background Agent 使用 Max Mode，需要訂閱
2. **費用較高** - Background Agent 每次任務都會消耗額度
3. **API Key** - 從 Cursor Dashboard 取得，不會過期
4. **完全遠端** - 不需要開啟 Cursor IDE
5. **GitHub 整合** - 必須指定 GitHub 倉庫才能使用
6. **安全性** - 只有 `TELEGRAM_ALLOWED_USERS` 中的用戶可以使用
7. **Python 版本** - 建議使用 Python 3.11 或 3.12，不支援 3.13+
8. **Docker 推薦** - 使用 Docker 可避免所有環境問題

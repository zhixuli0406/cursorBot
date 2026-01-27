# CursorBot

透過 Telegram 和 Discord 遠端控制 Cursor Background Agent。

靈感來自 [cursor-telegram-bot](https://github.com/Hormold/cursor-telegram-bot) 和 [ClawdBot](https://clawd.bot/)。

## 特點

### 多平台支援
- **Telegram** - 完整的 Telegram Bot 支援
- **Discord** - 完整的 Discord Bot 支援（斜線指令、按鈕）
- **WhatsApp** - WhatsApp Web 整合（透過 Node.js 橋接）
- **MS Teams** - Microsoft Teams Bot Framework 整合
- **Slack** - Slack 工作區整合（Socket Mode）
- **統一介面** - 所有平台使用相同的功能

### 核心功能
- **完全遠端** - 無需開啟 IDE，雲端執行
- **互動式按鈕** - 直覺的按鈕介面
- **語音訊息** - 發送語音自動轉錄為任務
- **圖片支援** - 發送圖片加入任務描述
- **即時通知** - 任務完成自動推送
- **持續輪詢** - 長時間任務自動追蹤，不會超時中斷

### 進階功能（對標 ClawdBot）
- **記憶系統** - 記住用戶偏好和對話歷史
- **技能系統** - 可擴展的技能（翻譯、摘要、計算機、提醒）
- **對話上下文** - 智慧追蹤多輪對話，支援對話壓縮
- **審批系統** - 敏感操作需要確認
- **排程任務** - 定時執行任務
- **Webhook** - 支援 GitHub/GitLab 事件觸發
- **Agent Loop** - 自主代理執行循環
- **Browser 工具** - 網頁自動化和截圖
- **代理工具** - 檔案操作、命令執行、網頁抓取

### v0.3 新增功能
- **Session 管理** - ClawdBot 風格的 Session 管理系統
  - 持久化 Session 存儲
  - 重置策略（每日/閒置/手動）
  - DM 範圍控制（main/per-peer/per-channel-peer）
  - 身份連結（跨平台用戶映射）
  - Token 追蹤與統計
- **Compaction** - 對話壓縮，自動摘要歷史對話以減少 Token 使用
- **Thinking Mode** - 支援 Claude Extended Thinking 深度思考模式
- **Subagents** - 子代理系統，可分解複雜任務給專門代理執行
- **Sandbox** - 沙盒執行，安全隔離執行程式碼（Docker/Subprocess）
- **TTS** - 語音輸出，支援 OpenAI、Edge TTS、ElevenLabs
- **OAuth** - OAuth 2.0 認證，支援 GitHub、Google、Discord 登入
- **Heartbeat** - 心跳機制，自動監控服務健康狀態
- **Retry** - 重試機制，指數退避自動重試失敗請求
- **Queue** - 任務佇列，優先級任務排程管理
- **Doctor** - 系統診斷工具，全面健康檢查
- **Reactions** - 訊息表情回應，UX 增強
- **Apply Patch** - Git 補丁應用與管理
- **Chunking** - 智慧訊息分塊，保留程式碼區塊完整性
- **Tool Policy** - 工具存取控制與審計
- **CLI Tool** - 命令列工具 `cursorbot`
- **WhatsApp** - WhatsApp 整合，透過 whatsapp-web.js 橋接
- **MS Teams** - Microsoft Teams 整合，Bot Framework 支援
- **iMessage** - macOS iMessage 整合，AppleScript 支援
- **Discord Voice** - Discord 語音頻道監聯與轉錄
- **Tailscale** - Tailscale VPN 整合，安全遠端存取
- **Chrome Extension** - 瀏覽器擴展，網頁整合
- **Moonshot AI** - 月之暗面 AI 整合，中國市場支援
- **GLM 智譜** - ChatGLM AI 整合，中國市場支援
- **Line Bot** - Line Messaging API 整合，亞洲市場
- **macOS Menu Bar** - macOS 選單列快速存取應用
- **Web Dashboard** - 網頁管理儀表板
- **WebChat** - 瀏覽器即時聊天介面
- **Control UI** - 網頁控制台配置管理

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

#### 5. 設定 AI 提供者（多模型支援）

`/agent` 指令支援多種 AI 提供者，只需在 `.env` 填入對應的 API Key 即可使用。

**支援的提供者：**

| 提供者 | 環境變數 | 說明 |
|--------|----------|------|
| OpenAI | `OPENAI_API_KEY` | GPT-4o, GPT-3.5-turbo 等 |
| Google Gemini | `GOOGLE_GENERATIVE_AI_API_KEY` | Gemini 2.0, 1.5 Pro 等 |
| Anthropic | `ANTHROPIC_API_KEY` | Claude 3.5 Sonnet, Opus 等 |
| OpenRouter | `OPENROUTER_API_KEY` | 代理多種模型（推薦） |
| Ollama | `OLLAMA_ENABLED=true` | 本地模型（Llama, Mistral 等） |
| 自訂端點 | `CUSTOM_API_BASE` | 相容 OpenAI API 的端點 |

**方案一：OpenRouter（推薦）**

一個 API Key 即可存取多種模型，包含免費選項。

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
```

取得 API Key：[openrouter.ai/keys](https://openrouter.ai/keys)

**方案二：OpenAI**

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

可用模型：`gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `o1-preview`, `o1-mini`

取得 API Key：[platform.openai.com/api-keys](https://platform.openai.com/api-keys)

**方案三：Anthropic Claude**

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

可用模型：`claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, `claude-3-haiku-20240307`

取得 API Key：[console.anthropic.com](https://console.anthropic.com/)

**方案四：Google Gemini**

```env
GOOGLE_GENERATIVE_AI_API_KEY=AIzaSyxxxxxxxxxx
GOOGLE_MODEL=gemini-2.0-flash
```

可用模型：`gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-pro`

取得 API Key：[aistudio.google.com/apikey](https://aistudio.google.com/apikey)

**方案五：Ollama（本地模型）**

不需要 API Key，在本地執行模型。

```env
OLLAMA_ENABLED=true
OLLAMA_API_BASE=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

安裝 Ollama：[ollama.ai](https://ollama.ai/)

```bash
# 安裝後執行
ollama pull llama3.2
ollama serve
```

可用模型：`llama3.2`, `llama3.1`, `mistral`, `codellama`, `phi3`, `qwen2.5`

**方案六：ElevenLabs TTS（可選）**

高品質語音合成服務。

```env
ELEVENLABS_API_KEY=your_api_key
```

取得 API Key：[elevenlabs.io](https://elevenlabs.io/)

**方案七：自訂端點**

支援任何相容 OpenAI API 的端點（如 LM Studio, vLLM, LocalAI）。

```env
CUSTOM_API_BASE=http://localhost:1234/v1
CUSTOM_API_KEY=optional-key
CUSTOM_MODEL=local-model
```

**指定預設提供者：**

```env
# 強制使用特定提供者
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o
```

**自動選擇優先順序：**
1. OpenRouter（如果設定了 `OPENROUTER_API_KEY`）
2. OpenAI（如果設定了 `OPENAI_API_KEY`）
3. Anthropic（如果設定了 `ANTHROPIC_API_KEY`）
4. Google Gemini（如果設定了 `GOOGLE_GENERATIVE_AI_API_KEY`）
5. Ollama（如果設定了 `OLLAMA_ENABLED=true`）
6. 自訂端點（如果設定了 `CUSTOM_API_BASE`）

#### 6. 啟動服務

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
⏱️ 執行時間: 5分30秒
📝 結果: ...

[🔗 在 Cursor 開啟] [💬 追問] [📋 複製結果]
```

**持續輪詢功能：**

Background Agent 任務會持續輪詢直到完成或失敗，不會因超時而中斷：
- 自動追蹤任務狀態直到最終結果
- 執行中每 30 秒更新一次狀態訊息
- 顯示已執行時間，讓你掌握進度
- 即使長時間任務也能正確獲得結果

```
🔄 任務執行中...

🆔 abc12345
📊 狀態: running
⏱️ 已執行: 5分30秒

任務仍在執行，請耐心等候...
```

## 指令說明

### 基礎指令

| 指令 | 說明 |
|------|------|
| `/start` | 啟動 Bot |
| `/help` | 顯示說明 |
| `/status` | 系統狀態 |
| `/doctor` | 系統診斷 |
| `/sessions` | 會話管理 |

### AI 對話

| 指令 | 說明 |
|------|------|
| `/ask <問題>` | 發送問題給 Cursor Background Agent |
| `/agent <任務>` | 啟動 Agent Loop 執行複雜任務 |
| `/model` | 查看目前使用的 AI 模型 |
| `/model list` | 列出所有可用模型 |
| `/model set <provider> [model]` | 切換 AI 模型 |
| `/model reset` | 恢復預設模型 |
| `/repo <owner/repo>` | 切換 GitHub 倉庫 |
| `/repos` | 查看帳號中所有的 GitHub 倉庫 |
| `/tasks` | 查看我的任務列表 |
| `/result <ID>` | 查看任務結果 |
| `/cancel_task <ID>` | 取消執行中的任務 |
| `/tts <文字>` | 文字轉語音 |

### 系統管理（v0.3）

| 指令 | 說明 |
|------|------|
| `/doctor` | 系統診斷，檢查配置與健康狀態 |
| `/doctor quick` | 快速健康檢查 |
| `/sessions` | 顯示會話統計 |
| `/sessions list` | 列出活躍會話 |
| `/sessions prune` | 清理過期會話 |
| `/patch` | 查看補丁管理說明 |
| `/patch create` | 從當前變更建立補丁 |
| `/patch list` | 查看補丁歷史 |
| `/policy` | 顯示工具策略狀態 |
| `/policy list` | 列出所有策略 |
| `/policy audit` | 查看審計日誌 |
| `/tts <文字>` | 文字轉語音 |
| `/tts providers` | 列出可用 TTS 服務 |
| `/broadcast <訊息>` | 廣播訊息給所有用戶 |
| `/usage` | 顯示使用統計 |
| `/usage me` | 顯示我的使用統計 |
| `/permissions` | 顯示權限系統狀態 |
| `/permissions user <id>` | 查看用戶權限 |
| `/permissions group` | 群組權限設定 |
| `/elevate` | 查看提升狀態 |
| `/elevate <分鐘>` | 請求權限提升 |
| `/lock` | 查看閘道鎖定狀態 |
| `/lock on` | 鎖定 Bot |
| `/lock off` | 解鎖 Bot |
| `/lock maintenance [分鐘]` | 進入維護模式 |
| `/location` | 位置服務 |
| `/location share` | 分享位置 |
| `/route` | 頻道路由狀態 |
| `/route list` | 列出頻道 |
| `/presence` | 查看在線狀態 |
| `/presence online/away/busy` | 設定狀態 |
| `/gateway` | 統一閘道資訊 |
| `/agents` | 列出已註冊代理 |
| `/control` | 系統控制面板 |
| `/control status` | 系統狀態 |
| `/control providers` | AI 提供者列表 |
| `/control url` | Web 介面網址 |
| `/mode` | 查看/切換對話模式 |
| `/mode auto` | 自動選擇最佳模式 ⭐ (預設) |
| `/mode cli` | 切換到 Cursor CLI 模式 |
| `/mode agent` | 切換到 Agent Loop 模式 |
| `/mode cursor` | 切換到 Background Agent 模式 |
| `/chatinfo` | 查看 CLI 對話上下文資訊 |
| `/newchat` | 清除 CLI 對話記憶，開始新對話 |
| `/climodel` | 查看 CLI 模型設定 |
| `/climodel list` | 列出所有 CLI 可用模型 |
| `/climodel set <model>` | 切換 CLI 模型 |
| `/climodel reset` | 恢復 CLI 預設模型 |
| `/tui` | 終端介面說明 |
| `/whatsapp` | WhatsApp 整合狀態 |
| `/whatsapp qr` | 顯示 WhatsApp 登入 QR Code |
| `/teams` | MS Teams 整合狀態 |
| `/tailscale` | Tailscale VPN 狀態 |
| `/tailscale devices` | 列出 Tailscale 裝置 |
| `/tailscale ping <device>` | Ping Tailscale 裝置 |
| `/imessage` | iMessage 狀態 (macOS) |
| `/imessage chats` | 列出 iMessage 聊天 |
| `/imessage send <recipient> <msg>` | 發送 iMessage |
| `/line` | Line Bot 狀態 |
| `/line setup` | Line 設定說明 |
| `/menubar` | macOS Menu Bar 說明 |

**模型切換範例：**

```
/model                              # 查看目前狀態
/model list                         # 列出所有模型
/model set openai gpt-4o            # 使用 OpenAI GPT-4o
/model set anthropic                # 使用 Anthropic (預設模型)
/model set ollama llama3.2          # 使用本地 Ollama
/model reset                        # 恢復預設
```

**CLI 對話記憶功能：**

Cursor CLI 模式支援對話記憶，可以延續之前的對話上下文：

```
/mode cli                           # 切換到 CLI 模式
(直接發送訊息)                       # 開始對話，自動建立上下文
(繼續發送)                           # 延續上一個對話
/chatinfo                           # 查看目前對話資訊
/newchat                            # 清除記憶，開始新對話
```

**CLI 模型選擇功能：**

Cursor CLI 支援多種 AI 模型，可以根據需求切換：

```
/climodel                           # 查看目前 CLI 模型設定
/climodel list                      # 列出所有可用模型
/climodel set sonnet-4.5            # 使用 Claude 4.5 Sonnet
/climodel set gpt-5.2               # 使用 GPT-5.2
/climodel set gemini-3-pro          # 使用 Gemini 3 Pro
/climodel set opus-4.5-thinking     # 使用 Claude 4.5 Opus (Thinking)
/climodel reset                     # 恢復預設模型
```

**可用 CLI 模型（部分列表）：**
| 模型 ID | 說明 |
|---------|------|
| `auto` | 自動選擇（預設） |
| `gpt-5.2` | GPT-5.2 |
| `gpt-5.2-codex` | GPT-5.2 Codex（程式碼專用） |
| `opus-4.5` | Claude 4.5 Opus |
| `opus-4.5-thinking` | Claude 4.5 Opus (Thinking) |
| `sonnet-4.5` | Claude 4.5 Sonnet |
| `sonnet-4.5-thinking` | Claude 4.5 Sonnet (Thinking) |
| `gemini-3-pro` | Gemini 3 Pro |
| `gemini-3-flash` | Gemini 3 Flash |
| `grok` | Grok |

**`/ask` vs `/agent` 的差別：**

| | `/ask` | `/agent` |
|---|--------|----------|
| 後端 | Cursor Background Agent | 可切換（OpenAI/Claude/Gemini 等） |
| 用途 | 程式碼相關任務 | 通用 AI 對話和分析 |
| 需要 | Cursor Pro 訂閱 | OpenRouter 或 Gemini API Key |
| 特點 | 可直接修改 GitHub 倉庫 | 多步驟推理、通用問答 |

**倉庫切換範例：**
```
/repo lizhixu/cursorBot
/repo https://github.com/facebook/react
```

**Agent Loop 範例：**
```
/agent 幫我分析這個系統的架構
/agent 寫一份專案規劃書
/agent 解釋什麼是 RAG
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
| `/diagnose` | 診斷終端環境（Docker/本地） |

### 工作區管理

| 指令 | 說明 |
|------|------|
| `/workspace` | 顯示工作區 |
| `/workspace list` | 列出所有工作區（分頁顯示） |
| `/cd <名稱>` | 切換工作區 |
| `/search <關鍵字>` | 搜尋程式碼 |

**分頁功能：**

`/workspace list` 支援分頁顯示所有工作區：
- 每頁顯示 10 個工作區
- 顯示總數量和當前頁碼
- 支援「上一頁」「下一頁」導航
- 「重新整理」按鈕可重新載入列表

```
📂 可用工作區

共 35 個工作區（第 1/4 頁）

[📁 project-a]
[📁 project-b ✓]  ← 當前工作區
...

[📄 1/4] [下一頁 ▶️]
[🔄 重新整理] [❌ 關閉]
```

### 記憶與技能（對標 ClawBot）

| 指令 | 說明 |
|------|------|
| `/memory` | 查看記憶 |
| `/memory add <key> <value>` | 新增記憶 |
| `/memory get <key>` | 取得記憶 |
| `/memory del <key>` | 刪除記憶 |
| `/skills` | 查看所有可用技能 |
| `/skills agent` | 查看 Agent 技能 |
| `/translate <lang> <text>` | 翻譯 |
| `/calc <expression>` | 計算 |
| `/remind <time> <message>` | 設定提醒 |

### Agent 技能系統

Agent 技能是 `/agent` 指令可以使用的工具，讓 AI 能執行實際操作。

**內建 Agent 技能：**

| 技能名稱 | 說明 |
|----------|------|
| `web_search` | 搜尋網路資訊（使用 DuckDuckGo） |
| `code_analysis` | 分析程式碼品質和問題 |
| `file_read` | 讀取工作區檔案 |
| `execute_command` | 執行終端指令 |
| `url_fetch` | 擷取網頁內容 |

**UI/UX Pro Max Agent Skills（已安裝）：**

| 技能名稱 | 說明 |
|----------|------|
| `uiux_design_system` | 生成完整的 UI/UX 設計系統建議 |
| `uiux_search` | 搜尋 UI 風格、色彩調色盤、字體排版 |
| `uiux_stack` | 取得特定技術堆疊的 UI/UX 指南 |
| `uiux_checklist` | 取得 UI/UX 交付前檢查清單 |

> 基於 [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
> 包含 67 種 UI 風格、96 種色彩調色盤、57 種字體組合、100 條推理規則

**使用範例：**

```
/agent 幫我搜尋 Python 非同步程式設計的教學
/agent 分析 src/main.py 的程式碼品質
/agent 讀取 README.md 並摘要重點
/agent 執行 npm install 並告訴我結果

# UI/UX 設計相關
/agent 幫我設計一個 SaaS 儀表板的 UI 風格
/agent 為美容 SPA 網站生成設計系統
/agent 搜尋 glassmorphism 風格指南
/agent 取得 React 的 UI 效能最佳實踐
```

**自訂 Agent 技能：**

將技能檔案放入 `skills/agent/` 目錄，系統會自動偵測並載入。支援多種格式：

**方式一：簡單 Python 檔案（推薦）**

```python
# skills/agent/my_skill.py
# 只需定義 SKILL_INFO 和 execute 函數即可！

SKILL_INFO = {
    "name": "my_skill",
    "description": "My custom skill",
    "parameters": {"input": "Input text"},
    "examples": ["Example usage"],
}

async def execute(input: str = "", **kwargs) -> dict:
    return {"result": input.upper()}
```

**方式二：JSON 配置檔案**

```json
// skills/agent/my_api.skill.json
{
  "name": "my_api",
  "description": "Call external API",
  "type": "http",
  "url": "https://api.example.com/endpoint",
  "method": "POST",
  "parameters": {"query": "Search query"}
}
```

**方式三：Shell 指令技能**

```json
// skills/agent/disk_check.skill.json
{
  "name": "disk_check",
  "description": "Check disk usage",
  "type": "command",
  "command": "df -h",
  "timeout": 10
}
```

**方式四：完整 Python 類別**

```python
# skills/agent/advanced_skill.py
from src.core.skills import AgentSkill, AgentSkillInfo

class AdvancedSkill(AgentSkill):
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="advanced_skill",
            description="Advanced skill with full control",
        )
    
    async def execute(self, **kwargs) -> dict:
        return {"result": "Success"}
```

**支援的技能類型：**

| 類型 | 檔案格式 | 說明 |
|------|----------|------|
| Python 函數 | `*.py` + `SKILL_INFO` | 最簡單，自動封裝 |
| Python 類別 | `*.py` + `AgentSkill` 子類 | 完整控制 |
| HTTP API | `*.skill.json` + `type: "http"` | 呼叫外部 API |
| Shell 指令 | `*.skill.json` + `type: "command"` | 執行系統指令 |
| 腳本執行 | `*.skill.json` + `type: "script"` | 執行外部腳本 |
| YAML 配置 | `*.skill.yaml` | 同 JSON，支援 YAML 格式 |

### 系統管理

| 指令 | 說明 |
|------|------|
| `/stats` | 使用統計 |
| `/settings` | 用戶設定 |
| `/schedule` | 查看排程 |
| `/clear` | 清除對話上下文 |

### v0.3 進階功能

#### TTS 語音輸出

支援將文字轉換為語音，可透過程式碼使用：

```python
from src.core import text_to_speech, TTSProvider

# 使用 OpenAI TTS
result = await text_to_speech("你好，這是語音測試", provider="openai")

# 使用免費的 Edge TTS
result = await text_to_speech("你好", provider="edge", voice="zh-TW-HsiaoChenNeural")

# 使用 ElevenLabs 高品質語音
result = await text_to_speech("Hello", provider="elevenlabs", voice="rachel")
```

**支援的 TTS 提供者：**

| 提供者 | 環境變數 | 說明 |
|--------|----------|------|
| OpenAI | `OPENAI_API_KEY` | 高品質，6 種聲音 |
| Edge TTS | 無需 API Key | 免費，多語言支援 |
| ElevenLabs | `ELEVENLABS_API_KEY` | 最高品質，自然語音 |

#### Sandbox 沙盒執行

安全執行不受信任的程式碼：

```python
from src.core import execute_code, SandboxType

# 使用 Subprocess 執行 Python
result = await execute_code("print('Hello')", language="python")

# 使用 Docker 隔離執行
result = await execute_code(
    "console.log('Hello')",
    language="javascript",
    sandbox_type="docker",
    timeout=30.0
)
```

**支援的沙盒類型：**

| 類型 | 說明 | 隔離等級 |
|------|------|----------|
| `subprocess` | 子程序執行 | 低 |
| `docker` | Docker 容器 | 高 |
| `restricted` | 受限 Python | 中 |

#### Subagents 子代理系統

將複雜任務分解給專門的子代理執行：

```python
from src.core import get_subagent_orchestrator, SubagentType

orchestrator = get_subagent_orchestrator()

# 自動分解任務
plan = await orchestrator.plan_task("實作一個 REST API 並撰寫測試")
result = await orchestrator.execute_plan(plan)
```

**子代理類型：**

| 類型 | 說明 |
|------|------|
| `researcher` | 資訊蒐集 |
| `coder` | 程式碼撰寫 |
| `reviewer` | 程式碼審查 |
| `planner` | 任務規劃 |
| `analyst` | 資料分析 |
| `writer` | 文件撰寫 |

#### Thinking Mode（Claude Extended Thinking）

使用 Claude 的深度思考模式處理複雜問題：

```python
from src.core import get_llm_manager

manager = get_llm_manager()

# 啟用 Thinking Mode
response = await manager.generate(
    messages,
    provider="anthropic",
    thinking=True,
    thinking_budget=10000  # 思考 token 預算
)
```

#### 對話壓縮（Compaction）

自動壓縮長對話歷史以節省 Token：

```python
from src.core import get_context_manager

ctx_manager = get_context_manager()
ctx = ctx_manager.get_context(user_id, chat_id)

# 檢查是否需要壓縮
if ctx.needs_compaction():
    await ctx.compact()  # 自動摘要舊訊息

# 取得包含摘要的上下文
messages = ctx.get_context_with_summary()
```

#### Session 管理（ClawdBot-style）

參考 [ClawdBot Session Management](https://docs.clawd.bot/concepts/session) 實現的 Session 管理系統：

```python
from src.core.session import get_session_manager, ChatType, DMScope

# 取得 session manager
session_mgr = get_session_manager()

# 取得或建立 session
session = session_mgr.get_session(
    user_id="123456",
    chat_id="123456",
    chat_type=ChatType.DM,
    channel="telegram",
)

# 查看 session 狀態
status = session_mgr.get_session_status(session.session_key)
print(f"Token 使用: {status['total_tokens']}")
print(f"訊息數: {status['message_count']}")

# 重置 session（開始新對話）
new_session = session_mgr.reset_session(
    user_id="123456",
    chat_id="123456",
    chat_type=ChatType.DM,
    channel="telegram",
)

# 統計資訊
stats = session_mgr.get_stats()
print(f"總 Sessions: {stats['total_sessions']}")
```

**Session 指令：**

| 指令 | 說明 |
|------|------|
| `/session` | 查看目前 session 資訊 |
| `/session list` | 列出所有 sessions |
| `/session stats` | 統計資訊 |
| `/session reset` | 重置當前 session |
| `/session config` | 查看設定 |
| `/new` | 開始新對話（重置所有上下文） |
| `/status` | 狀態總覽 |
| `/compact` | 壓縮對話歷史 |

**環境變數設定：**

```env
# DM 範圍模式
# main = 所有 DM 共用 (預設)
# per-peer = 每人獨立
# per-channel-peer = 每頻道每人獨立
SESSION_DM_SCOPE=main

# 重置模式
# daily = 每日重置 (預設)
# idle = 閒置重置
# manual = 手動重置
SESSION_RESET_MODE=daily

# 每日重置時間 (0-23)
SESSION_RESET_HOUR=4

# 閒置分鐘數
SESSION_IDLE_MINUTES=120
```

#### 任務佇列

優先級任務排程：

```python
from src.core import get_task_queue, TaskPriority

queue = get_task_queue()
await queue.start()

# 提交任務
task_id = await queue.submit(
    my_async_function,
    arg1, arg2,
    priority=TaskPriority.HIGH,
    timeout=60.0
)

# 等待結果
task = await queue.wait_for_task(task_id)
```

#### 心跳監控

監控服務健康狀態：

```python
from src.core import get_heartbeat_monitor

monitor = get_heartbeat_monitor()

# 註冊服務健康檢查
monitor.register_service(
    "database",
    health_check=check_db_connection,
    recovery_handler=reconnect_db
)

await monitor.start()
```

#### 重試機制

自動重試失敗的請求：

```python
from src.core import with_retry, RetryConfig

@with_retry(max_retries=3, initial_delay=1.0)
async def call_external_api():
    # 失敗會自動重試
    return await api.request()
```

#### CLI 工具

CursorBot 提供命令列工具 `cursorbot` 進行管理：

```bash
# 查看系統狀態
./cursorbot status

# 運行診斷
./cursorbot doctor

# 查看配置
./cursorbot config

# 查看日誌
./cursorbot logs -n 100

# 查看會話
./cursorbot sessions

# 啟動 Bot
./cursorbot start

# 發送訊息給用戶
./cursorbot message --user-id 123456 --text "Hello"

# 廣播訊息
./cursorbot broadcast --text "System announcement"

# 重置 Bot 資料
./cursorbot reset --confirm
```

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
│   │   ├── context.py           # 對話上下文 + Compaction
│   │   ├── approvals.py         # 審批系統
│   │   ├── scheduler.py         # 排程任務
│   │   ├── webhooks.py          # Webhook 處理
│   │   ├── tools.py             # 代理工具
│   │   ├── browser.py           # 瀏覽器自動化
│   │   ├── agent_loop.py        # Agent 執行循環
│   │   ├── llm_providers.py     # 多 LLM 提供者管理
│   │   ├── heartbeat.py         # 心跳監控 + 重試機制
│   │   ├── queue.py             # 任務佇列
│   │   ├── tts.py               # 語音合成（TTS）
│   │   ├── subagents.py         # 子代理系統
│   │   ├── sandbox.py           # 沙盒執行
│   │   └── oauth.py             # OAuth 認證
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
| `/ask <問題>` | 發送問題給 Cursor Agent |
| `/agent <任務>` | 啟動 Agent Loop（OpenRouter/Gemini） |
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

### 環境診斷

如果終端機指令無法正常執行，可以使用診斷指令檢查環境狀態：

```
/diagnose
```

這會顯示：
- 運行環境類型（Docker/本地）
- 工作目錄狀態
- 可用的工具（git、node、npm、python 等）
- 用戶權限資訊
- 基本指令執行測試

### 進入容器終端

如需直接進入容器操作：

```bash
docker exec -it cursorbot /bin/bash
```

### 容器內可用工具

Docker 映像已包含：
- Python 3.12 + pip
- Node.js 20.x + npm
- Git
- Playwright（Chromium）
- 建置工具（build-essential）
- 常用工具：curl、wget、jq、tree、htop、nano、vim
- 網路工具：ping、nslookup、netstat

### 安全注意事項

- 掛載的目錄在容器內可完全存取
- 避免掛載系統敏感目錄（如 `/`, `C:\Windows`）
- 建議只掛載專案工作目錄
- 容器使用非 root 用戶（UID 1000）運行

### Git SSH 認證（可選）

如果需要在容器內使用 Git SSH 認證，可以在 `docker-compose.yml` 中取消註解 SSH 掛載：

```yaml
volumes:
  - ~/.ssh:/home/cursorbot/.ssh:ro
```

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

### Docker 終端機指令問題

**問題：** `/run` 指令無法執行或找不到檔案

**診斷步驟：**
1. 執行 `/diagnose` 查看環境狀態
2. 確認 `CURSOR_WORKSPACE_PATH` 在 `.env` 中正確設定
3. 確認該路徑在主機上實際存在

**解決方案：**

```bash
# 1. 停止並重建容器
docker compose down
docker compose up -d --build

# 2. 檢查掛載是否成功
docker exec -it cursorbot ls -la /workspace

# 3. 如果權限問題，檢查主機目錄權限
ls -la /path/to/your/workspace
```

**問題：** 權限被拒絕（Permission denied）

**原因：** Docker 容器使用 UID 1000 運行，但主機目錄可能屬於其他用戶。

**解決方案：**
```bash
# 方法一：更改主機目錄權限
chmod -R 755 /path/to/your/workspace

# 方法二：更改目錄擁有者
sudo chown -R 1000:1000 /path/to/your/workspace
```

**問題：** 找不到 git/node/npm 等工具

**原因：** 使用舊版映像。

**解決方案：**
```bash
# 重新建置映像（不使用快取）
docker compose build --no-cache
docker compose up -d
```

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

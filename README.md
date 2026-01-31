# CursorBot

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](docs/FEATURE_ROADMAP.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

多平台 AI 語音助手，支援 Telegram、Discord、LINE、Slack、WhatsApp、Teams、Google Chat 及原生應用。說「Hey Cursor」即可喚醒，整合 GPT、Claude、Gemini 等 AI 模型，支援語音辨識、自然對話、智慧家居控制、會議助手等功能。

靈感來自 [cursor-telegram-bot](https://github.com/Hormold/cursor-telegram-bot) 和 [ClawdBot](https://clawd.bot/)。

> 📋 **功能路線圖**: 查看 [docs/FEATURE_ROADMAP.md](docs/FEATURE_ROADMAP.md) 了解完整的功能清單與開發進度。

## 特點

### 多平台支援
- **Telegram** - 完整的 Telegram Bot 支援
- **Discord** - 完整的 Discord Bot 支援（斜線指令、按鈕）
- **LINE** - LINE Messaging API 整合（亞洲市場）
- **Slack** - Slack Events API + 斜線指令
- **WhatsApp** - WhatsApp Cloud API 整合
- **MS Teams** - Microsoft Teams Bot Framework 整合
- **Google Chat** - Google Workspace 整合
- **統一指令系統** - 所有平台使用相同的指令（`/help`, `/status` 等）
- **統一 Webhook** - 簡化的 webhook 端點（`/webhook/line`, `/webhook/slack` 等）

### 核心功能
- **🚀 異步執行（預設）** - 所有請求背景處理，完成後自動推送結果
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

#### 多平台 Webhook 整合
- **統一 Webhook 端點** - 所有社群平台使用統一的 API Server
  - `/webhook/line` - LINE Messaging API
  - `/webhook/slack` - Slack Events API
  - `/webhook/slack/commands` - Slack 斜線指令
  - `/webhook/whatsapp` - WhatsApp Cloud API
  - `/webhook/teams` - Microsoft Teams Bot Framework
  - `/webhook/google-chat` - Google Chat
- **統一指令系統** - 所有平台支援相同指令（`/help`, `/status`, `/model` 等）
- **使用者權限控制** - 各平台可設定允許的使用者 ID

#### CLI 模型選擇
- Cursor CLI 支援多種 AI 模型切換
  - GPT-5.2 系列（含 Codex 程式碼專用版）
  - Claude 4.5 Opus / Sonnet（含 Thinking 深度思考版）
  - Gemini 3 Pro / Flash
  - Grok
  - 使用 `/climodel` 指令管理

#### SkillsMP 技能市集整合
- **10萬+ 開源技能** - 支援 [SkillsMP.com](https://skillsmp.com) 技能市集
- **多種安裝格式**：
  - GitHub 縮寫：`/skills_install github:owner/repo/path`
  - GitHub URL：`/skills_install https://github.com/...`
  - SkillsMP ID：`/skills_install owner-repo-path-skill-md`
- **SKILL.md 標準** - 相容 Anthropic/OpenAI 的開放技能格式

#### TUI 終端介面
- **互動式終端 UI** - 美觀的終端聊天介面
- **Rich 支援** - 使用 rich 函式庫提供豐富格式
- **CLI 工具整合** - `./cursorbot tui` 或 `./cursorbot chat`

#### 其他新功能
- **Session 管理** - ClawdBot 風格的 Session 管理系統
- **Compaction** - 對話壓縮，自動摘要歷史對話以減少 Token 使用
- **Thinking Mode** - 支援 Claude Extended Thinking 深度思考模式
- **Subagents** - 子代理系統，可分解複雜任務給專門代理執行
- **Sandbox** - 沙盒執行，安全隔離執行程式碼
- **TTS** - 語音輸出（OpenAI、Edge TTS、ElevenLabs）
- **OAuth** - OAuth 2.0 認證
- **Heartbeat** - 心跳監控機制
- **Queue** - 任務佇列
- **Doctor** - 系統診斷工具
- **RAG** - 檢索增強生成
  - 支援多種文件格式（PDF、Markdown、程式碼、JSON）
  - 智慧文字分塊
  - 多種嵌入提供者（OpenAI、Google、Ollama）
  - 向量儲存（ChromaDB）
- **異步執行（v0.4 預設）** - 所有模式預設背景執行
  - CLI/Agent 模式皆為異步
  - 任務完成自動推送結果
  - `/tasks` 查看任務、`/cancel` 取消任務
  - 並行任務支援

### v0.4 新增功能

#### MCP (Model Context Protocol)
- **Anthropic MCP 標準** - 支援 Anthropic 的 Model Context Protocol
- **MCP Server 管理** - 連接、斷開多個 MCP 伺服器
- **工具與資源** - 存取 MCP 提供的工具和資源
- 使用 `/mcp` 指令管理

#### Workflow Engine（工作流程引擎）
- **宣告式工作流程** - YAML/JSON 定義多步驟自動化任務
- **條件執行** - 支援條件判斷與分支
- **並行處理** - 步驟可並行或序列執行
- **錯誤處理** - 自動重試與錯誤恢復
- 使用 `/workflow` 指令管理

#### Analytics（使用分析）
- **事件追蹤** - 追蹤訊息、指令、AI 請求等事件
- **用戶統計** - 個人使用量與成本估算
- **每日報告** - 自動生成每日統計
- **資料匯出** - 支援 JSON/CSV 匯出
- 使用 `/analytics` 指令查看

#### Code Review（程式碼審查）
- **自動化審查** - AI 驅動的程式碼品質分析
- **靜態分析** - 整合 pylint、ruff、eslint
- **安全掃描** - 檢測常見安全漏洞
- **Git Diff 審查** - 支援審查變更內容
- 使用 `/review` 指令執行

#### Conversation Export（對話匯出）
- **多種格式** - JSON、Markdown、HTML、TXT、CSV
- **隱私保護** - 自動遮蔽敏感資訊
- **篩選功能** - 依日期、使用者篩選
- 使用 `/export` 指令匯出

#### Auto-Documentation（自動文件生成）
- **程式碼文件** - 從 docstring 生成文件
- **API 參考** - 自動生成 API 文件
- **README 生成** - 智慧生成專案說明
- 使用 `/docs` 指令生成

#### v0.4 進階功能

##### Multiple Gateways（多閘道高可用）
- **負載平衡** - Round-robin、最少連接、加權隨機
- **自動故障轉移** - Gateway 失敗自動切換
- **健康監控** - 定期檢查 Gateway 狀態
- **Session 親和** - 可選的 Sticky Sessions

##### DM Pairing（設備配對）
- **配對碼** - 6 位數數字配對碼
- **QR Code** - 支援 QR Code 掃碼配對
- **多設備** - 每個用戶支援多設備
- **設備管理** - 查看、解除配對設備

##### Live Canvas（A2UI 視覺工作區）
- **即時渲染** - WebSocket 即時更新
- **豐富組件** - 文字、程式碼、表格、圖表
- **互動元素** - 按鈕、輸入框、滑桿
- **多人協作** - 分享 Canvas 給其他用戶

##### 多語系支援（i18n）
- **繁體中文** - 預設語言
- **簡體中文** - zh-CN
- **英文** - English
- **日文** - 日本語

##### 郵件自動分類
- **智慧分類** - 自動辨識郵件類型
- **優先級偵測** - 識別緊急郵件
- **自訂規則** - 新增個人分類規則
- **多種類別** - 社交、促銷、更新、通知等

##### 原生應用（Native Apps）
- **macOS App** - SwiftUI 原生應用，支援 Menu Bar、Talk Mode、Live Canvas
- **iOS Node** - iPhone/iPad 原生應用，支援相機拍攝、裝置配對
- **Android Node** - Kotlin/Jetpack Compose 原生應用，完整功能支援
- **WebSocket Gateway** - 透過 `/ws/node` 端點即時連線
- **跨平台同步** - Canvas、訊息、設定多裝置同步

### v1.1 語音助手（Voice Assistant）

CursorBot v1.1 新增了類似 Siri 的智慧語音助手功能：

#### 核心功能
- **多喚醒詞支援** - 自訂喚醒詞（「嘿 Cursor」「小助手」「ok cursor」）
- **離線語音辨識** - 使用 Vosk/Whisper 本地辨識，無需網路
- **自然語音合成** - 支援 Edge TTS、ElevenLabs、OpenAI TTS
- **環境噪音過濾** - WebRTC VAD 智慧過濾背景噪音
- **喚醒音效回饋** - 喚醒成功/失敗的音效提示

#### 意圖識別與指令
- **系統控制** - 「調高音量」「截圖」「鎖定螢幕」
- **應用程式** - 「打開 Cursor」「關閉 Chrome」
- **程式碼操作** - 「Git commit」「執行測試」「建置專案」
- **網頁搜尋** - 「搜尋天氣」「打開 GitHub」
- **提醒功能** - 「提醒我10分鐘後喝水」
- **檔案操作** - 「新建檔案」「刪除這個」「重新命名」
- **剪貼簿** - 「複製這個」「貼上」「剪貼簿歷史」
- **即時翻譯** - 「翻譯成英文」「這個怎麼說」
- **天氣查詢** - 「今天天氣如何」「明天需要帶傘嗎」
- **日曆整合** - 「今天有什麼會議」「明天的行程」

#### 情境感知
- **時間感知** - 根據時段自動調整問候語和建議
- **位置感知** - 識別家/辦公室環境
- **應用感知** - 根據正在使用的應用調整回應
- **習慣學習** - 學習用戶習慣並提供個人化建議

#### 個人化學習
- **使用模式分析** - 自動學習常用指令
- **快捷指令** - 自訂語音快捷方式
- **回應風格** - 友善/專業/輕鬆風格切換
- **偏好記憶** - 記住用戶喜好設定

#### 進階功能
- **聲紋識別** - 只回應特定用戶的語音
- **情緒語調** - 根據內容自動調整語調（開心、嚴肅、疑問）
- **語音中斷** - 說話時可被打斷，立即回應新指令
- **會議助手** - 會議錄音、即時轉錄、摘要生成、行動項目提取
- **語音導航** - 「跳到第 50 行」「找函數 main」IDE 語音控制
- **智慧家居** - HomeKit/Google Home/小米 IoT 語音控制
- **離線 TTS** - 使用 Piper/eSpeak 本地語音合成
- **多語言回應** - 自動偵測語言並切換回應語言

#### 快速開始語音助手

```bash
# 安裝依賴
pip install vosk edge-tts numpy

# 下載 Vosk 模型（中文）
# https://alphacephei.com/vosk/models
# 解壓至 models/vosk-model-small-cn

# 執行語音助手示範
python examples/voice_assistant_demo.py

# 純文字模式測試（無需麥克風）
python examples/voice_assistant_demo.py --text
```

#### 環境變數設定（.env）
```env
# 喚醒設定
VOICE_WAKE_ENABLED=true
VOICE_WAKE_WORDS=hey cursor,ok cursor,小助手

# 語音辨識
VOICE_STT_ENGINE=whisper_local
VOICE_VOSK_MODEL_PATH=models/vosk-model-small-cn

# 語音合成
VOICE_TTS_ENGINE=edge
VOICE_TTS_VOICE=zh-TW-HsiaoChenNeural

# 助手設定
VOICE_ASSISTANT_NAME=小助手
VOICE_RESPONSE_STYLE=friendly
```

### v0.4 快速指令參考

| 功能 | 指令 | 說明 |
|------|------|------|
| **異步執行** | 直接發送訊息 | 所有模式預設背景執行 |
| | `/tasks` | 查看待處理任務 |
| | `/cancel <id>` | 取消任務 |
| | `/mode cli` | 切換 CLI 模式（異步） |
| | `/mode agent` | 切換 Agent 模式（異步） |
| **程式碼審查** | `/review <檔案>` | AI 程式碼審查 |
| | `/review dir <目錄>` | 審查整個目錄 |
| | `/review diff` | 審查 Git 變更 |
| **工作流程** | `/workflow` | 工作流程狀態 |
| | `/workflow list` | 列出工作流程 |
| | `/workflow run <名稱>` | 執行工作流程 |
| **使用分析** | `/analytics` | 使用統計總覽 |
| | `/analytics me` | 我的使用統計 |
| | `/analytics daily` | 每日統計 |
| | `/analytics export` | 匯出分析資料 |
| **對話匯出** | `/export` | 匯出為 Markdown |
| | `/export json` | 匯出為 JSON |
| | `/export html` | 匯出為 HTML |
| **文件生成** | `/docs <檔案>` | 生成檔案文件 |
| | `/docs api <目錄>` | 生成 API 文件 |
| | `/docs readme` | 生成 README |
| **MCP** | `/mcp` | MCP 狀態 |
| | `/mcp servers` | 列出 MCP 伺服器 |
| | `/mcp tools` | 列出 MCP 工具 |
| | `/mcp connect <名稱> <指令>` | 連接 MCP 伺服器 |

### v0.4 進階功能指令

| 功能 | 指令 | 說明 |
|------|------|------|
| **多閘道** | `/gateways` | 閘道叢集狀態 |
| | `/gateways list` | 列出所有閘道 |
| | `/gateways add <id> <host> <port>` | 新增閘道 |
| | `/gateways strategy <type>` | 設定負載平衡策略 |
| **設備配對** | `/pair` | 產生配對碼 |
| | `/pair qr` | 產生 QR Code |
| | `/pair <code>` | 使用配對碼配對 |
| | `/devices` | 列出已配對設備 |
| | `/devices remove <id>` | 解除配對 |
| **Live Canvas** | `/canvas` | Canvas 狀態 |
| | `/canvas new [名稱]` | 新建 Canvas |
| | `/canvas list` | 列出 Canvas |
| | `/canvas add <type> <content>` | 新增元件 |
| | `/canvas clear` | 清空 Canvas |
| **多語系** | `/lang` | 目前語言設定 |
| | `/lang list` | 列出可用語言 |
| | `/lang set <code>` | 切換語言 |
| **郵件分類** | `/classify` | 分類功能狀態 |
| | `/classify <內容>` | 分類郵件內容 |
| | `/classify rules` | 顯示分類規則 |

## 運作原理

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Telegram   │────▶│             │────▶│ Cursor CLI  │
│  Discord    │────▶│  CursorBot  │────▶│ AI Providers│
│  LINE       │────▶│  (API Server│────▶│ (OpenAI,    │
│  Slack      │────▶│   + Bot)    │◀────│  Claude,    │
│  WhatsApp   │◀────│             │◀────│  Gemini...) │
└─────────────┘     └─────────────┘     └─────────────┘
```

1. 你在任何支援的平台發送問題
2. CursorBot 統一處理指令和訊息
3. 根據模式調用 Cursor CLI 或 AI 提供者
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

# === 工作區設定 ===
CURSOR_WORKSPACE_PATH=/path/to/your/projects

# === CLI 模式設定（可選）===
CURSOR_CLI_MODEL=auto
CURSOR_CLI_TIMEOUT=300
```

#### 4. 設定 AI 提供者（多模型支援）

`/agent` 指令支援多種 AI 提供者，只需在 `.env` 填入對應的 API Key 即可使用。

**支援的提供者：**

| 提供者 | 環境變數 | 說明 |
|--------|----------|------|
| OpenAI | `OPENAI_API_KEY` | GPT-4o, GPT-3.5-turbo 等 |
| Google Gemini | `GOOGLE_GENERATIVE_AI_API_KEY` | Gemini 2.0, 1.5 Pro 等 |
| Anthropic | `ANTHROPIC_API_KEY` | Claude 3.5 Sonnet, Opus 等 |
| OpenRouter | `OPENROUTER_API_KEY` | 代理多種模型（推薦） |
| GitHub Copilot | `COPILOT_TOKEN` 或 `GITHUB_TOKEN` + `COPILOT_ENABLED=true` | 原生 Copilot API (需訂閱) |
| Ollama | `OLLAMA_ENABLED=true` | 本地模型（Llama, Mistral 等） |
| Minimax | `MINIMAX_API_KEY` | 中國市場 (abab6.5s-chat 等) |
| 自訂端點 | `CUSTOM_API_BASE` | 相容 OpenAI API 的端點 |

**方案一：OpenRouter（推薦）**

一個 API Key 即可存取多種模型，包含免費選項。

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
OPENROUTER_MODEL=google/gemini-3-flash-preview:free
```

免費模型（2026）：
- `google/gemini-3-flash-preview:free` - Google Gemini 3 Flash（推薦）
- `mistral/devstral-2-2512:free` - 123B 程式碼專用模型
- `deepseek/deepseek-r1-0528:free` - 強大推理能力
- `meta-llama/llama-3.3-70b-instruct:free` - Meta Llama 3.3

取得 API Key：[openrouter.ai/keys](https://openrouter.ai/keys)

**方案二：OpenAI**

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxx
OPENAI_MODEL=gpt-5-main-mini
```

最新模型（2026）：
| 模型 | 說明 |
|------|------|
| `gpt-5.2` | 最新 GPT-5.2 系列 |
| `gpt-5-main` | GPT-5 主模型（高通量） |
| `gpt-5-main-mini` | GPT-5 輕量版（推薦） |
| `gpt-5-thinking` | 深度推理模型 |
| `gpt-5-thinking-mini` | 輕量推理模型 |
| `gpt-5-thinking-nano` | 超輕量推理（開發者） |
| `o3` | OpenAI o3（傳統） |
| `gpt-4o` | GPT-4o（穩定版） |

取得 API Key：[platform.openai.com/api-keys](https://platform.openai.com/api-keys)

**方案三：Anthropic Claude**

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

最新模型（2026）：
| 模型 | 說明 |
|------|------|
| `claude-opus-4-5-20251101` | Claude 4.5 Opus（最強大） |
| `claude-sonnet-4-5-20250929` | Claude 4.5 Sonnet（推薦） |
| `claude-sonnet-4-20250514` | Claude 4 Sonnet |
| `claude-3-5-sonnet-20241022` | Claude 3.5 Sonnet（穩定） |

取得 API Key：[console.anthropic.com](https://console.anthropic.com/)

**方案四：Google Gemini**

```env
GOOGLE_GENERATIVE_AI_API_KEY=AIzaSyxxxxxxxxxx
GOOGLE_MODEL=gemini-3-flash-preview
```

最新模型（2026）：
| 模型 | 說明 |
|------|------|
| `gemini-3-pro-preview` | Gemini 3 Pro（最強多模態） |
| `gemini-3-flash-preview` | Gemini 3 Flash（推薦） |
| `gemini-3-pro-image-preview` | 圖像生成與編輯 |
| `gemini-2.5-pro` | Gemini 2.5 Pro（穩定） |
| `gemini-2.5-flash` | Gemini 2.5 Flash |
| `gemini-2.5-flash-lite` | 輕量高效模型 |

取得 API Key：[aistudio.google.com/apikey](https://aistudio.google.com/apikey)

**方案五：Ollama（本地模型）**

不需要 API Key，在本地執行模型。

```env
OLLAMA_ENABLED=true
OLLAMA_API_BASE=http://localhost:11434
OLLAMA_MODEL=llama3.3
```

安裝 Ollama：[ollama.ai](https://ollama.ai/)

```bash
# 安裝後執行
ollama pull llama3.3
ollama serve
```

最新模型（2026）：
| 模型 | 說明 |
|------|------|
| `llama3.3` | Meta Llama 3.3（推薦） |
| `qwen3` | 阿里 Qwen 3 系列 |
| `qwen3-coder` | Qwen 3 程式碼專用 |
| `deepseek-r1` | DeepSeek 推理模型 |
| `deepseek-v3.2` | DeepSeek V3.2 |
| `mistral-large-3` | Mistral 企業級模型 |
| `gemma3` | Google Gemma 3 |
| `phi-4` | Microsoft Phi-4 |

**方案六：GitHub Copilot（原生 API）**

使用 GitHub Copilot 訂閱，透過原生 Copilot API 進行對話。

**方法一：使用 Copilot Token（推薦）**

如果你已經有 VS Code Copilot 擴充套件，可以直接取得 token：

```env
COPILOT_TOKEN=ghu_xxxxxxxxxxxx
COPILOT_ENABLED=true
COPILOT_MODEL=gpt-4o
```

取得 Copilot Token 的方式：
1. 在 VS Code 中開啟開發者工具（Help > Toggle Developer Tools）
2. 在 Console 中執行：`await require('vscode').authentication.getSession('github', ['copilot'])`
3. 複製回傳的 `accessToken`

**方法二：使用 GitHub Token**

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
COPILOT_ENABLED=true
COPILOT_MODEL=gpt-4o
```

**設定步驟：**
1. 確認你有有效的 **GitHub Copilot 訂閱**（Individual/Business/Enterprise）
2. 前往 [github.com/settings/tokens](https://github.com/settings/tokens)
3. 建立 **Personal Access Token (classic)**
4. 勾選以下權限：
   - `read:user` - 讀取使用者資料
   - `user:email` - 讀取 email
   - `copilot` - Copilot API 存取（如果可見）

> ⚠️ 必須要有有效的 GitHub Copilot 訂閱才能使用
> ⚠️ 如果出現 401/403 錯誤，請確認你的 Copilot 訂閱狀態

可用模型：
| 模型 | 說明 |
|------|------|
| `gpt-4o` | OpenAI GPT-4o（推薦） |
| `gpt-4o-mini` | OpenAI GPT-4o Mini |
| `gpt-4-turbo` | OpenAI GPT-4 Turbo |
| `gpt-4` | OpenAI GPT-4 |
| `gpt-3.5-turbo` | OpenAI GPT-3.5 Turbo |
| `claude-3.5-sonnet` | Anthropic Claude 3.5 Sonnet |
| `o1-preview` | OpenAI o1 推理模型 |
| `o1-mini` | OpenAI o1 Mini |

**方案七：ElevenLabs TTS（可選）**

高品質語音合成服務。

```env
ELEVENLABS_API_KEY=your_api_key
```

取得 API Key：[elevenlabs.io](https://elevenlabs.io/)

**方案八：自訂端點**

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
2. GitHub Copilot（如果設定了 `COPILOT_ENABLED=true`）
3. OpenAI（如果設定了 `OPENAI_API_KEY`）
4. Anthropic（如果設定了 `ANTHROPIC_API_KEY`）
5. Google Gemini（如果設定了 `GOOGLE_GENERATIVE_AI_API_KEY`）
6. Ollama（如果設定了 `OLLAMA_ENABLED=true`）
7. 自訂端點（如果設定了 `CUSTOM_API_BASE`）

**方案八：Cursor CLI 模型設定（可選）**

Cursor CLI 模式 (`/mode cli`) 可以使用不同的模型，這些模型由 Cursor 直接提供。

```env
# CLI 預設模型（可選，不設定則使用 CLI 預設值）
CURSOR_CLI_MODEL=sonnet-4.5

# CLI 超時時間（秒，預設 300）
CURSOR_CLI_TIMEOUT=300

# 禁用 CLI 對話記憶（如果 --resume 功能有問題）
# 設為 1, true 或 yes 來禁用
CLI_DISABLE_RESUME=
```

可用的 CLI 模型包括：
| 模型 ID | 說明 |
|---------|------|
| `auto` | 自動選擇（預設） |
| `gpt-5.2` | GPT-5.2 |
| `gpt-5.2-codex` | GPT-5.2 Codex（程式碼專用） |
| `opus-4.5-thinking` | Claude 4.5 Opus (Thinking) |
| `sonnet-4.5` | Claude 4.5 Sonnet |
| `gemini-3-pro` | Gemini 3 Pro |
| `grok` | Grok |

使用 `/climodel list` 查看完整列表，使用 `/climodel set <model>` 切換。

#### 5. Gateway 設定（原生應用連線）

如果需要使用原生應用（macOS/iOS/Android）連接到 CursorBot，需要設定 Gateway。

```env
# Gateway Token（可選，留空則允許所有連線）
# 正式環境建議設定 Token
GATEWAY_TOKEN=your_secret_token_here

# Gateway 功能開關
GATEWAY_CHAT_ENABLED=true
GATEWAY_CANVAS_ENABLED=true
GATEWAY_PAIRING_ENABLED=true
GATEWAY_IMAGE_ANALYSIS_ENABLED=true
```

**原生應用連線設定：**

| 設定項目 | 說明 | 範例 |
|----------|------|------|
| Gateway URL | WebSocket 連線位址 | `http://your-server-ip:8000` |
| Token | 認證 Token（與 `GATEWAY_TOKEN` 對應） | 留空或填入 Token |

**WebSocket 端點：**
- 連線位址：`ws://{SERVER_HOST}:{SERVER_PORT}/ws/node`
- 已連線節點查詢：`GET /api/nodes`

**支援的訊息類型：**

| 類型 | 功能 |
|------|------|
| `chat` | 與 AI 對話 |
| `canvas` | Live Canvas 操作（建立、更新、刪除） |
| `pairing` | 裝置配對（取得配對碼、驗證） |
| `image` | 圖像分析（需要視覺模型） |
| `command` | 系統指令（status、ping） |

**原生應用下載：**

應用程式碼位於 `apps/` 目錄：
- `apps/macos/` - macOS 應用（SwiftUI）
- `apps/ios/` - iOS 應用（SwiftUI）
- `apps/android/` - Android 應用（Kotlin）

詳細建置說明請參考各目錄中的 `README.md`。

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

### 1. 選擇對話模式

```
/mode cli
→ ✅ 已切換至 CLI 模式
```

或使用 `/mode agent` 切換到 Agent 模式。

### 2. 發送任務

**文字訊息:**
```
幫我實作一個快速排序函數
→ 🤖 正在處理...
→ ✅ 完成！
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

**對話模式：**

CursorBot 支援多種對話模式：
- **CLI 模式** - 使用 Cursor CLI 執行任務
- **Agent 模式** - 使用 Agent Loop 多步驟推理
- **Auto 模式** - 自動選擇最佳模式

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
| `/agent <任務>` | 啟動 Agent Loop 執行任務 |
| `/model` | 查看目前使用的 AI 模型 |
| `/model list` | 列出所有可用模型 |
| `/model set <provider> [model]` | 切換 AI 模型 |
| `/model reset` | 恢復預設模型 |
| `/climodel` | 查看 CLI 模型設定 |
| `/climodel list` | 列出所有 CLI 可用模型 |
| `/climodel set <model>` | 切換 CLI 模型 |
| `/climodel reset` | 恢復 CLI 預設模型 |
| `/mode` | 查看/切換對話模式 |
| `/mode cli` | 切換到 Cursor CLI 模式 |
| `/mode agent` | 切換到 Agent Loop 模式 |
| `/new` | 開始新對話 |
| `/clear` | 清除對話上下文 |
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
| `/mode auto` | 自動選擇模式 |
| `/chatinfo` | 查看 CLI 對話上下文資訊 |
| `/newchat` | 清除 CLI 對話記憶，開始新對話 |
| `/climodel` | 查看 CLI 模型設定 |
| `/climodel list` | 列出所有 CLI 可用模型 |
| `/climodel set <model>` | 切換 CLI 模型 |
| `/climodel reset` | 恢復 CLI 預設模型 |
| `/tui` | 終端介面說明 |

### v0.4 新功能指令

| 指令 | 說明 |
|------|------|
| `/mcp` | MCP (Model Context Protocol) 狀態 |
| `/mcp servers` | 列出已連接的 MCP 伺服器 |
| `/mcp tools` | 列出可用的 MCP 工具 |
| `/mcp connect <name> <cmd>` | 連接 MCP 伺服器 |
| `/workflow` | 工作流程引擎狀態 |
| `/workflow list` | 列出可用工作流程 |
| `/workflow run <name>` | 執行工作流程 |
| `/analytics` | 使用分析總覽 |
| `/analytics me` | 我的使用統計 |
| `/analytics daily` | 每日統計 |
| `/analytics export` | 匯出分析資料 |
| `/review <file>` | 程式碼審查 |
| `/review dir <path>` | 審查目錄 |
| `/review diff` | 審查 Git 變更 |
| `/export` | 匯出對話（Markdown） |
| `/export json` | 匯出為 JSON |
| `/export html` | 匯出為 HTML |
| `/docs <file>` | 生成檔案文件 |
| `/docs api <dir>` | 生成 API 文件 |
| `/docs readme` | 生成 README |

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

### v1.1 語音助手指令

| 指令 | 說明 |
|------|------|
| `/voice` | 語音助手狀態 |
| `/voice wake [on\|off]` | 開啟/關閉語音喚醒 |
| `/voice wake words <詞>` | 設定喚醒詞（逗號分隔） |
| `/voice stt [engine]` | 設定語音辨識引擎（whisper/vosk） |
| `/voice tts [engine]` | 設定語音合成引擎（edge/elevenlabs） |
| `/voice style [friendly\|professional]` | 設定回應風格 |
| `/meeting` | 會議助手狀態 |
| `/meeting start` | 開始會議錄音 |
| `/meeting stop` | 結束會議並生成摘要 |
| `/meeting notes` | 查看會議筆記 |
| `/meeting summary` | 取得會議摘要和行動項目 |
| `/smarthome` | 智慧家居狀態 |
| `/smarthome devices` | 列出已連接的智慧設備 |
| `/smarthome control <設備> <動作>` | 控制智慧設備 |
| `/offline` | 離線模式狀態 |
| `/offline on` | 啟用離線模式 |
| `/offline off` | 停用離線模式 |
| `/accessibility` | 無障礙設定 |
| `/accessibility screen_reader [on\|off]` | 螢幕閱讀器 |
| `/accessibility voice_nav [on\|off]` | 語音導航 |
| `/privacy` | 隱私設定 |
| `/privacy export` | 匯出我的資料 |
| `/privacy delete` | 刪除我的資料 |
| `/vocabulary` | 個人詞彙管理 |
| `/vocabulary add <詞> [發音]` | 新增個人詞彙 |

**語音指令範例：**

```
# 語音喚醒後說...
「打開 Cursor」          # 啟動應用程式
「調高音量」              # 系統控制
「截圖」                  # 螢幕截圖
「跳到第 50 行」         # IDE 導航
「今天有什麼會議」        # 日曆查詢
「開燈」                  # 智慧家居控制
「翻譯成英文」            # 即時翻譯
「提醒我 10 分鐘後開會」  # 提醒設定
```

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

**CLI 模式 vs Agent 模式：**

| | CLI 模式 | Agent 模式 |
|---|--------|----------|
| 後端 | Cursor CLI | LLM Provider（OpenAI/Claude/Gemini 等） |
| 用途 | 程式碼相關任務 | 通用 AI 對話和分析 |
| 需要 | Cursor CLI 安裝 | API Key |
| 特點 | 支援對話記憶、多種模型 | 多步驟推理、工具調用 |
| 切換 | `/mode cli` | `/mode agent` |

**Agent Loop 範例：**
```
/agent 幫我分析這個系統的架構
/agent 寫一份專案規劃書
/agent 解釋什麼是 RAG
```

### 每日行程提醒

每天早上自動發送當日行程提醒，支援所有平台。

| 指令 | 說明 |
|------|------|
| `/reminder` | 查看提醒設定 |
| `/reminder on` | 啟用每日提醒（預設 07:00） |
| `/reminder off` | 關閉提醒 |
| `/reminder time HH:MM` | 設定提醒時間 |
| `/reminder weekend [on\|off]` | 週末提醒設定 |
| `/reminder test` | 發送測試提醒 |

**功能特色：**
- 每日自動發送當天行程
- 自訂提醒時間（預設早上 7:00）
- 支援 Google Calendar 和 Apple Calendar
- 可設定週末不發送
- 包含行程摘要

**使用範例：**
```
/reminder on              # 啟用提醒
/reminder time 06:30      # 改為 6:30 發送
/reminder weekend off     # 週末不發送
```

### Google Calendar 整合

與 Google 日曆無縫整合，查看和管理你的行程。

| 指令 | 說明 |
|------|------|
| `/calendar` | 顯示今日行程 |
| `/calendar week` | 顯示本週行程 |
| `/calendar list` | 列出所有日曆 |
| `/calendar add <標題> <時間>` | 新增行程 |
| `/calendar auth` | 開始 Google 認證 |

**設定步驟：**
1. 前往 [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. 建立 OAuth 2.0 用戶端 ID（桌面應用程式）
3. 啟用 Google Calendar API
4. 下載 JSON 並儲存為 `data/google/credentials.json`
5. 執行 `/calendar auth` 進行認證

### Apple Calendar 整合 (macOS)

在 macOS 上整合 Apple Calendar，直接從 Bot 查看和管理行程。

| 指令 | 說明 |
|------|------|
| `/calendar` | 顯示今日行程 |
| `/calendar week` | 顯示本週行程 |
| `/calendar list` | 列出所有日曆 |
| `/calendar add <標題> <開始> <結束>` | 新增行程 |
| `/calendar help` | 查看說明 |

**時間格式**: `YYYY-MM-DDTHH:MM` (ISO 格式)

**範例**:
```
/calendar add 開會 2026-01-28T10:00 2026-01-28T11:00
```

**注意**: 僅在 macOS 上可用，需要授權 Calendar.app 自動化權限。

### Gmail 整合

讀取和發送 Gmail 郵件。

| 指令 | 說明 |
|------|------|
| `/gmail` | 顯示最近郵件 |
| `/gmail unread` | 顯示未讀數量 |
| `/gmail search <查詢>` | 搜尋郵件 |
| `/gmail send <收件人> <主旨> \| <內文>` | 發送郵件 |
| `/gmail labels` | 列出標籤 |
| `/gmail auth` | 開始 Google 認證 |

**搜尋範例：**
```
/gmail search from:example@gmail.com
/gmail search subject:報告 is:unread
/gmail search after:2026/01/01 has:attachment
```

### Google OAuth 常見問題

#### Q1: 顯示的應用程式名稱不正確（例如顯示其他專案名稱）

**原因**：OAuth 同意畫面顯示的名稱是在 Google Cloud Console 中設定的，不是由 `credentials.json` 決定。

**解決方案**：
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 選擇你的專案
3. 左側選單 →「API 和服務」→「OAuth 同意畫面」
4. 點擊「編輯應用程式」，將名稱改為 `CursorBot`

#### Q2: 顯示「未通過 Google 驗證」警告

**這是正常現象**。除非提交應用程式給 Google 審核，否則都會顯示此警告。

**解決方案**：
- 點擊「進階」→「前往 CursorBot（不安全）」繼續授權
- 或將你的 Google 帳號加入專案的「測試使用者」名單

#### Q3: 手機 Telegram 無法完成 OAuth 認證（localhost 問題）

**原因**：OAuth callback 設定為 `localhost`，手機無法訪問電腦的 localhost。

**解決方案**（擇一）：

1. **在電腦完成首次認證（推薦）**：
   ```bash
   # 在電腦執行認證腳本
   source venv/bin/activate
   python test_google_auth.py
   ```
   認證完成後會產生 `token.json`，之後手機就可以直接使用。

2. **使用公開 URL**：
   - 如果有部署伺服器，在 Google Cloud Console 新增公開的 redirect URI
   - 更新 `.env` 中的 `GOOGLE_OAUTH_REDIRECT_URI`

3. **使用 ngrok 暴露本地服務**：
   ```bash
   ngrok http 8080
   ```
   將 ngrok URL 加入 Google Cloud Console 的重新導向 URI

#### Q4: 找不到 credentials.json

**解決方案**：
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立專案或選擇現有專案
3. 啟用 Google Calendar API 和 Gmail API
4. 前往「API 和服務」→「憑證」
5. 建立「OAuth 2.0 用戶端 ID」（選擇「桌面應用程式」）
6. 下載 JSON 並儲存為 `data/google/credentials.json`

#### Q5: Token 過期或失效

**解決方案**：
```bash
# 刪除舊的 token 檔案
rm data/google/calendar_token.json
rm data/google/gmail_token.json

# 重新執行認證
python test_google_auth.py
```

#### Q6: 需要的 OAuth 範圍（Scopes）

| 功能 | 範圍 |
|------|------|
| Calendar 讀取 | `https://www.googleapis.com/auth/calendar.readonly` |
| Calendar 編輯 | `https://www.googleapis.com/auth/calendar.events` |
| Gmail 讀取 | `https://www.googleapis.com/auth/gmail.readonly` |
| Gmail 發送 | `https://www.googleapis.com/auth/gmail.send` |
| Gmail 修改 | `https://www.googleapis.com/auth/gmail.modify` |

### Skills Registry（技能市集）

搜尋、安裝和管理 AI 技能。支援 [SkillsMP.com](https://skillsmp.com) 的 10 萬+ 開源技能。

| 指令 | 說明 |
|------|------|
| `/skills` | 查看已安裝技能 |
| `/skills_search [關鍵字]` | 搜尋可用技能（本地 + GitHub） |
| `/skills_install <技能ID>` | 安裝技能 |
| `/skills_list` | 列出已安裝技能 |
| `/skills_uninstall <技能ID>` | 解除安裝技能 |

**支援的安裝格式：**

| 格式 | 範例 |
|------|------|
| 內建技能 ID | `/skills_install web-search` |
| GitHub 縮寫 | `/skills_install github:vercel/next.js/.claude/skills` |
| GitHub URL | `/skills_install https://github.com/facebook/react/...` |
| SkillsMP ID | `/skills_install facebook-react-claude-skills-test-skill-md` |

**從 SkillsMP.com 安裝技能：**
1. 前往 [skillsmp.com](https://skillsmp.com)
2. 搜尋想要的技能（如 React、Next.js 等）
3. 複製技能 ID
4. 使用 `/skills_install <ID>` 安裝

**內建技能：**
- `web-search` - 網路搜尋
- `code-analysis` - 程式碼分析
- `file-manager` - 檔案管理
- `git-helper` - Git 操作
- `translator` - 翻譯
- `calculator` - 計算機
- `weather` - 天氣查詢
- `json-tools` - JSON 處理
- `api-tester` - API 測試

### 多平台 Webhook 設定

所有社群平台都使用統一的 API Server（預設 port 8000）處理 webhook。

#### LINE 設定

1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 建立 Provider 和 Messaging API Channel
3. 取得 Channel Access Token 和 Channel Secret
4. 設定 Webhook URL: `https://你的domain:8000/webhook/line`
5. 開啟「Use webhook」選項

```env
LINE_ENABLED=true
LINE_CHANNEL_ACCESS_TOKEN=你的token
LINE_CHANNEL_SECRET=你的secret
LINE_ALLOWED_USERS=  # 可選，限制使用者
```

#### Slack 設定

1. 前往 [Slack API](https://api.slack.com/apps) 建立 App
2. 啟用 Event Subscriptions，設定 URL: `https://你的domain:8000/webhook/slack`
3. 訂閱 `message.channels` 和 `message.im` 事件
4. 設定 Slash Commands URL: `https://你的domain:8000/webhook/slack/commands`

```env
SLACK_ENABLED=true
SLACK_BOT_TOKEN=xoxb-你的token
SLACK_SIGNING_SECRET=你的signing_secret
SLACK_ALLOWED_USERS=  # 可選
```

#### WhatsApp Cloud API 設定

1. 前往 [Meta for Developers](https://developers.facebook.com/)
2. 建立 WhatsApp Business App
3. 設定 Webhook URL: `https://你的domain:8000/webhook/whatsapp`
4. 設定驗證 Token（自訂）

```env
WHATSAPP_ENABLED=true
WHATSAPP_ACCESS_TOKEN=你的access_token
WHATSAPP_VERIFY_TOKEN=你的自訂驗證token
WHATSAPP_PHONE_NUMBER_ID=你的phone_number_id
WHATSAPP_ALLOWED_NUMBERS=  # 可選
```

#### MS Teams 設定

1. 前往 [Azure Portal](https://portal.azure.com/) 註冊 Bot
2. 建立 Azure AD App Registration
3. 設定 Messaging Endpoint: `https://你的domain:8000/webhook/teams`

```env
TEAMS_ENABLED=true
TEAMS_APP_ID=你的app_id
TEAMS_APP_PASSWORD=你的app_password
TEAMS_ALLOWED_USERS=  # 可選
```

#### Google Chat 設定

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 啟用 Chat API
3. 建立服務帳戶
4. 設定 Webhook URL: `https://你的domain:8000/webhook/google-chat`

```env
GOOGLE_CHAT_ENABLED=true
GOOGLE_CHAT_CREDENTIALS=data/google/chat_service_account.json
GOOGLE_CHAT_ALLOWED_USERS=  # 可選
```

### Signal 整合

隱私優先的 Signal 通訊整合。

**設定步驟：**
1. 安裝 [signal-cli](https://github.com/AsamK/signal-cli)
2. 註冊或連結電話號碼
3. 設定環境變數：
   ```
   SIGNAL_ENABLED=true
   SIGNAL_PHONE_NUMBER=+886912345678
   ```

### Google Chat 整合

與 Google Workspace 整合，支援 Google Chat 訊息。

**設定步驟：**
1. 在 Google Cloud Console 啟用 Chat API
2. 建立服務帳戶並下載憑證
3. 設定環境變數：
   ```
   GOOGLE_CHAT_ENABLED=true
   GOOGLE_CHAT_CREDENTIALS=data/google/chat_service_account.json
   ```

### Voice Wake 語音喚醒

使用語音喚醒詞啟動對話。

| 設定 | 說明 |
|------|------|
| `VOICE_WAKE_ENGINE` | 引擎：vosk, porcupine |
| `VOICE_WAKE_WORDS` | 喚醒詞（逗號分隔） |
| `VOSK_MODEL_PATH` | Vosk 模型路徑 |

**支援的喚醒引擎：**
- **Vosk** - 免費離線語音辨識
- **Porcupine** - Picovoice 高精度喚醒

### Talk Mode 持續對話

持續語音對話模式，支援即時語音轉文字和文字轉語音。

**功能：**
- 語音活動偵測（VAD）
- 即時語音轉文字（STT）
- 文字轉語音回應（TTS）
- 對話上下文保持

**支援的 STT 引擎：** Whisper、Vosk、Google Cloud  
**支援的 TTS 引擎：** ElevenLabs、Edge TTS、Google Cloud

### Agent to Agent 協作

跨 session 的多代理人協作系統。

**功能：**
- Session 發現與註冊
- 跨 session 訊息傳遞
- 任務委派與結果收集
- 多代理人工作流程

**使用範例：**
```python
from src.core.agent_to_agent import get_a2a_manager

a2a = get_a2a_manager()
await a2a.start(name="Main", capabilities=["code", "research"])

# 列出活躍 session
sessions = await a2a.list_sessions()

# 委派任務
result = await a2a.delegate_task(session_id, "分析這段程式碼...")
```

### 異步執行（背景任務）

Agent 和 CLI 支援背景執行模式，不需要等待任務完成，完成後自動推送結果。

| 指令 | 說明 |
|------|------|
| `/agent_async <任務>` | 背景執行 Agent |
| `/cli_async <任務>` | 背景執行 CLI |
| `/rag_async <問題>` | 背景執行 RAG 查詢 |
| `/tasks` | 查看你的待處理任務 |
| `/cancel <task_id>` | 取消任務 |
| `/task_status <task_id>` | 查看任務詳情 |
| `/task_stats` | 任務管理器統計 |

**使用範例：**

```
# 提交背景任務
/agent_async 分析這個專案的架構並撰寫文件

# 系統會立即回覆任務 ID
🚀 Task Submitted
Task ID: abc12345
Type: Agent

# 繼續使用 Bot 做其他事
/help
/status

# 任務完成後自動推送結果
✅ Task Completed

[任務結果...]
```

**特點：**
- 不需要等待 - 提交後立即返回
- 自動推送 - 完成後自動發送結果
- 任務追蹤 - 可查看所有任務狀態
- 可取消 - 支援取消進行中的任務
- 並行執行 - 支援多個任務同時執行

### RAG（檢索增強生成）

RAG 系統讓你可以索引文件並基於內容進行問答。

**自動對話記憶功能：**
- `/agent` 模式的對話會自動存入 RAG
- CLI 模式的對話會自動存入 RAG
- 使用 `/rag` 可以基於過往對話進行問答

| 指令 | 說明 |
|------|------|
| `/rag <問題>` | 基於索引內容回答問題 |
| `/index <檔案>` | 索引單一檔案 |
| `/index_dir <目錄>` | 索引整個目錄 |
| `/index_url <網址>` | 索引網頁內容 |
| `/index_text <文字>` | 索引手動輸入的文字 |
| `/search <關鍵字>` | 搜尋索引內容（不生成回答） |
| `/ragstats` | 查看 RAG 統計資訊 |
| `/ragconfig` | 配置 RAG 設定 |
| `/ragclear confirm` | 清除所有索引 |

**支援的檔案格式：**
- 文字：`.txt`, `.log`
- Markdown：`.md`, `.markdown`, `.mdx`
- 程式碼：`.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, `.cpp` 等
- PDF：`.pdf`（需安裝 pypdf）
- JSON：`.json`, `.jsonl`

**使用範例：**

```
# 索引專案文件
/index README.md
/index_dir docs/

# 基於索引內容提問
/rag 這個專案的主要功能是什麼？
/rag 如何設定環境變數？

# 搜尋特定內容
/search authentication
/search API key
```

**環境變數設定：**

```env
# RAG 嵌入設定（使用已配置的 AI 提供者）
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=50
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_PERSIST_DIR=data/rag
RAG_COLLECTION=default
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

# 啟動 TUI 終端介面
./cursorbot tui

# 互動式聊天（輕量版 TUI）
./cursorbot chat
./cursorbot chat --model opus-4.5

# 發送訊息給用戶
./cursorbot message --user-id 123456 --text "Hello"

# 廣播訊息
./cursorbot broadcast --text "System announcement"

# 重置 Bot 資料
./cursorbot reset --confirm
```

#### TUI 終端介面

美觀的終端使用者介面，支援互動式 AI 對話。

**安裝依賴：**
```bash
pip install rich
```

**啟動方式：**
```bash
# 完整 TUI 介面
./cursorbot tui

# 簡易聊天模式
./cursorbot chat

# 或直接執行模組
python -m src.cli.tui
```

**TUI 內建指令：**
| 指令 | 說明 |
|------|------|
| `/help` | 顯示幫助 |
| `/status` | 系統狀態 |
| `/model` | 顯示目前模型 |
| `/clear` | 清除聊天 |
| `/export` | 匯出聊天記錄 |
| `/quit` | 退出 |

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
│   │   ├── google_handlers.py   # Google/Skills 處理
│   │   └── keyboards.py         # 按鈕佈局
│   ├── channels/                # 多平台支援
│   │   ├── base.py              # Channel 抽象層
│   │   ├── manager.py           # Channel 管理器
│   │   ├── discord_channel.py   # Discord 實現
│   │   └── discord_handlers.py  # Discord 處理器
│   ├── cli/                     # CLI 工具
│   │   └── tui.py               # Terminal UI
│   ├── cursor/                  # Cursor 整合
│   │   ├── agent.py             # 工作區管理
│   │   ├── cli_agent.py         # Cursor CLI Agent
│   │   ├── file_operations.py
│   │   └── terminal.py
│   ├── core/                    # 核心功能
│   │   ├── unified_commands.py  # 統一指令系統
│   │   ├── skills_registry.py   # 技能市集（含 SkillsMP）
│   │   ├── memory.py            # 記憶系統
│   │   ├── skills.py            # 技能系統
│   │   ├── context.py           # 對話上下文
│   │   ├── agent_loop.py        # Agent 執行循環
│   │   ├── llm_providers.py     # 多 LLM 提供者
│   │   ├── session.py           # Session 管理
│   │   ├── rag.py               # RAG 系統
│   │   ├── tts.py               # 語音合成
│   │   └── ...
│   ├── platforms/               # 社群平台整合
│   │   ├── line_bot.py          # LINE Bot
│   │   ├── slack_bot.py         # Slack Bot
│   │   ├── whatsapp_bot.py      # WhatsApp Bot
│   │   ├── teams_bot.py         # MS Teams Bot
│   │   └── google_chat_bot.py   # Google Chat Bot
│   ├── server/                  # API Server
│   │   ├── api.py               # FastAPI 主程式
│   │   └── social_webhooks.py   # 社群平台 Webhook
│   └── utils/                   # 工具模組
├── skills/                      # 自訂技能
│   └── agent/                   # Agent 技能
├── data/                        # 資料儲存
├── cursorbot                    # CLI 工具入口
├── Dockerfile
├── docker-compose.yml
├── start.bat / start.sh
├── env.example
├── requirements.txt
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
| `/model` | 模型管理 |
| `/climodel` | CLI 模型管理 |
| `/mode` | 對話模式切換 |
| `/agent <任務>` | 啟動 Agent Loop |
| `/memory` | 記憶管理 |
| `/workspace` | 工作區管理 |
| `/skills` | 技能管理 |

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

1. **Cursor CLI** - 使用 CLI 模式需安裝 Cursor CLI（`agent` 指令）
2. **AI 提供者** - 至少需要設定一個 AI 提供者（OpenRouter、OpenAI、Gemini 等）
3. **多平台** - 各平台需要獨立設定 API Token 和 Webhook
4. **安全性** - 建議設定 `ALLOWED_USERS` 限制使用者
5. **Python 版本** - 建議使用 Python 3.11 或 3.12，不支援 3.13+
6. **Docker 推薦** - 使用 Docker 可避免所有環境問題
7. **GitHub Token** - 搜尋 SkillsMP/GitHub 技能時建議設定 `GITHUB_TOKEN` 提高 API 限制
8. **HTTPS** - 社群平台 Webhook 需要 HTTPS，本地測試可用 ngrok

## 版本資訊

| 版本 | 日期 | 說明 |
|------|------|------|
| v1.1.0 | 2026-01-29 | 語音助手、喚醒詞、聲紋識別、智慧家居、會議助手、無障礙支援 |
| v1.0.0 | 2026-01-28 | 正式版本、Live Canvas、原生應用、Multi-Gateway |
| v0.4.0 | 2026-01-27 | MCP、Workflow、Analytics、進階功能 |
| v0.3.0 | - | CLI 整合、Session 管理、RAG |
| v0.2.0 | - | 多平台支援、Agent Loop |
| v0.1.0 | - | 基礎 Telegram Bot |

> 📋 完整開發進度請查看 [docs/FEATURE_ROADMAP.md](docs/FEATURE_ROADMAP.md)

## 授權

MIT License

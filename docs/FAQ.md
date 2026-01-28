# CursorBot FAQ (常見問題)

## 目錄

- [安裝問題](#安裝問題)
- [Telegram 設定](#telegram-設定)
- [AI 模型問題](#ai-模型問題)
- [指令使用](#指令使用)
- [錯誤排除](#錯誤排除)
- [進階功能](#進階功能)

---

## 安裝問題

### Q: 支援哪些 Python 版本？

**A:** CursorBot 支援 **Python 3.10 - 3.12**。Python 3.13+ 目前不支援，因為部分依賴套件尚未相容。

Windows 用戶使用 `start.bat` 啟動時，腳本會自動檢測並安裝適合的 Python 版本。

### Q: 安裝時出現 `pydantic-core` 編譯錯誤？

**A:** 這通常發生在以下情況：

1. **Python 版本過新** - 請使用 Python 3.11 或 3.12
2. **缺少 Rust** - 安裝 [Rust](https://rustup.rs)
3. **最簡單的解決方案** - 使用 Docker：
   ```bash
   docker compose up -d
   ```

### Q: 如何在 Docker 中執行？

**A:** 
```bash
# 複製環境變數檔案
cp env.example .env
# 編輯 .env 填入設定

# 啟動服務
docker compose up -d

# 查看日誌
docker compose logs -f
```

### Q: Windows 啟動腳本閃退？

**A:** 執行 `debug.bat` 來診斷問題，常見原因：

1. PowerShell 執行政策限制 - 以管理員身份執行：
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
2. 防毒軟體阻擋
3. 路徑包含中文或特殊字元

---

## Telegram 設定

### Q: 如何取得 Telegram Bot Token？

**A:**
1. 在 Telegram 搜尋 **@BotFather**
2. 發送 `/newbot`
3. 按照提示設定 Bot 名稱和用戶名
4. 複製 API Token（格式：`123456789:ABCdef...`）

### Q: 如何取得我的 Telegram User ID？

**A:**
1. 在 Telegram 搜尋 **@userinfobot**
2. 發送任意訊息
3. 它會回覆你的 User ID（純數字）

### Q: Bot 沒有回應訊息？

**A:** 檢查以下項目：

1. **Token 是否正確** - 在 `.env` 確認 `TELEGRAM_BOT_TOKEN`
2. **是否設定白名單** - 確認 `TELEGRAM_ALLOWED_USERS` 包含你的 User ID
3. **Bot 是否正在運行** - 查看日誌：
   ```bash
   docker compose logs -f
   # 或
   cat logs/cursorbot.log
   ```
4. **網路連線** - 確保可以連接 Telegram API

### Q: 如何允許多個用戶使用？

**A:** 在 `.env` 中用逗號分隔多個 User ID：
```env
TELEGRAM_ALLOWED_USERS=123456789,987654321,456789123
```

---

## AI 模型問題

### Q: 沒有設定任何 AI 提供者可以使用嗎？

**A:** 可以使用 **Cursor CLI 模式**，前提是你的電腦已安裝 Cursor 編輯器。使用 `/mode cli` 切換到 CLI 模式。

### Q: OpenRouter 有免費模型嗎？

**A:** 有，以下模型免費使用：
- `google/gemini-2.0-flash-exp:free`
- `mistral/devstral-2-2512:free`
- `deepseek/deepseek-r1-0528:free`
- `meta-llama/llama-3.3-70b-instruct:free`

設定方式：
```env
OPENROUTER_API_KEY=sk-or-v1-xxx
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
```

### Q: 如何切換 AI 模型？

**A:** 使用 `/model` 指令：
```
/model                        # 查看目前模型
/model list                   # 列出可用模型
/model set openai gpt-4o      # 切換到 OpenAI GPT-4o
/model set anthropic          # 切換到 Anthropic Claude
```

### Q: CLI 模式和 Agent 模式有什麼區別？

**A:**

| | CLI 模式 | Agent 模式 |
|---|---------|----------|
| 後端 | Cursor CLI | LLM API |
| 優點 | 程式碼能力強 | 通用對話、工具調用 |
| 需要 | Cursor 安裝 | API Key |
| 適用 | 程式碼相關任務 | 一般 AI 對話 |
| 切換 | `/mode cli` | `/mode agent` |

---

## 指令使用

### Q: 有哪些常用指令？

**A:**

| 指令 | 說明 |
|------|------|
| `/help` | 完整指令說明 |
| `/status` | 系統狀態 |
| `/mode` | 切換對話模式 |
| `/model` | 模型設定 |
| `/new` | 開始新對話 |
| `/clear` | 清除上下文 |
| `/agent <任務>` | 執行 AI 任務 |

### Q: 如何使用 RAG 知識庫？

**A:**
```
# 索引檔案
/index README.md
/index_dir docs/

# 基於索引內容提問
/rag 這個專案的主要功能是什麼？

# 搜尋
/search authentication
```

### Q: 如何建立指令別名？

**A:** 使用 `/alias` 指令（v0.4 新增）：
```
# 建立別名
/alias add gpt model set openai gpt-4o

# 使用別名
/gpt

# 查看所有別名
/alias

# 刪除別名
/alias remove gpt
```

### Q: 什麼是 Thinking Mode？

**A:** Thinking Mode 讓 AI 在回答前進行深度推理（需要支援的模型如 Claude）：
```
/think off      # 關閉
/think low      # 輕度推理
/think medium   # 標準推理
/think high     # 深度推理
/think xhigh    # 最大推理
```

---

## 錯誤排除

### Q: 出現 "Rate limit exceeded" 錯誤？

**A:** 請求過於頻繁，等待一段時間後再試。可以用 `/ratelimit` 查看限制狀態。

### Q: 出現 "Unauthorized" 錯誤？

**A:** 檢查：
1. API Key 是否正確
2. API Key 是否有效（未過期、未被撤銷）
3. 是否有足夠的額度

### Q: 出現 "Model not found" 錯誤？

**A:** 模型 ID 可能有誤，使用 `/model list` 或 `/climodel list` 查看可用模型。

### Q: Docker 容器無法啟動？

**A:**
```bash
# 查看錯誤日誌
docker compose logs

# 重新建構
docker compose build --no-cache
docker compose up -d
```

### Q: 如何查看詳細錯誤訊息？

**A:**
1. 啟用 Verbose 模式：`/verbose on`
2. 設定 DEBUG 日誌等級：`LOG_LEVEL=DEBUG`
3. 查看日誌檔案：`logs/cursorbot.log`

---

## 進階功能

### Q: 如何整合 Google Calendar？

**A:**
1. 前往 [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. 建立 OAuth 2.0 憑證
3. 啟用 Google Calendar API
4. 下載憑證到 `data/google/credentials.json`
5. 執行 `/calendar auth` 進行認證

### Q: 如何使用 Voice Wake（語音喚醒）？

**A:**
```env
VOICE_WAKE_ENGINE=vosk  # 或 porcupine
VOICE_WAKE_WORDS=hey bot,computer
VOSK_MODEL_PATH=data/vosk-model
```

需要額外安裝語音辨識模型。

### Q: 如何設定 Webhook？

**A:** 各平台 Webhook URL 格式：
```
LINE:        https://你的domain/webhook/line
Slack:       https://你的domain/webhook/slack
WhatsApp:    https://你的domain/webhook/whatsapp
Teams:       https://你的domain/webhook/teams
Google Chat: https://你的domain/webhook/google-chat
```

本地測試可使用 [ngrok](https://ngrok.com/) 產生公開 URL。

### Q: 如何備份資料？

**A:** 備份 `data/` 目錄，包含：
- `cursorbot.db` - 資料庫
- `memory/` - 記憶系統
- `sessions/` - 會話資料
- `rag/` - RAG 向量資料庫

---

## 取得幫助

如果以上 FAQ 無法解決你的問題：

1. **查看日誌** - `docker compose logs` 或 `logs/cursorbot.log`
2. **執行診斷** - `/doctor` 指令
3. **GitHub Issues** - 提交問題到專案 Issue Tracker
4. **Discord 社群** - 加入討論社群

---

*最後更新：2026-01-28 (v0.4.0)*

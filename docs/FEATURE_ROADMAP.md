# CursorBot Feature Roadmap

對標 [Clawdbot](https://docs.clawd.bot/) 的功能實作進度追蹤。

**最後更新**: 2026-01-27  
**總體完成度**: 98% (122/124)

---

## 目錄

1. [通訊平台支援](#1-通訊平台支援)
2. [AI 模型提供者](#2-ai-模型提供者)
3. [核心功能](#3-核心功能)
4. [群組功能](#4-群組功能)
5. [工具與代理](#5-工具與代理)
6. [媒體支援](#6-媒體支援)
7. [串流與格式](#7-串流與格式)
8. [網路與架構](#8-網路與架構)
9. [介面與管理](#9-介面與管理)
10. [安全與認證](#10-安全與認證)
11. [運維與監控](#11-運維與監控)
12. [部署支援](#12-部署支援)
13. [CLI 命令](#13-cli-命令)

---

## 1. 通訊平台支援

**完成度**: 58% (7/12)

| 狀態 | 功能 | Clawdbot 實現 | CursorBot 實現 | 優先級 | 備註 |
|:----:|------|--------------|---------------|:------:|------|
| ✅ | Telegram | grammY | python-telegram-bot | - | 已完成 |
| ✅ | Discord | discord.js | discord.py | - | 已完成 |
| ✅ | WhatsApp | Baileys | whatsapp-web.js | - | v0.3 新增 |
| ✅ | iMessage | imsg CLI | AppleScript | - | v0.3 新增 (macOS) |
| ✅ | Slack | Plugin | slack_sdk | - | v0.3 新增 |
| ⬜ | Mattermost | Plugin | - | 🟢 低 | 開源替代 |
| ⬜ | Signal | - | - | 🟢 低 | 隱私優先 |
| ✅ | MS Teams | - | botbuilder | - | v0.3 新增 |
| ⬜ | Matrix | - | - | 🟢 低 | 開源協議 |
| ✅ | Line | - | line-bot-sdk | - | v0.3 新增 |
| ⬜ | Google Chat | - | - | 🟢 低 | Google 生態 |
| ⬜ | Zalo | - | - | 🟢 低 | 越南市場 |

### 待辦事項

- [x] 研究 Baileys 庫實現 WhatsApp 整合
- [x] 實現 Slack Bot API 整合
- [x] 實現 MS Teams Bot 整合
- [x] 評估 iMessage 整合可行性

---

## 2. AI 模型提供者

**完成度**: 92% (11/12)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | OpenAI | GPT-4, GPT-3.5 | - | 已完成 |
| ✅ | Anthropic Claude | Claude 3.5 | - | 已完成 |
| ✅ | Google Gemini | Gemini 2.0 | - | 已完成 |
| ✅ | OpenRouter | 多模型代理 | - | 已完成 |
| ✅ | Ollama | 本地模型 | - | 已完成 |
| ✅ | Custom Endpoint | OpenAI 相容 | - | 已完成 |
| ✅ | Model Failover | 自動切換備用模型 | - | v0.2 新增 |
| ✅ | Usage Tracking | 使用量追蹤 | - | v0.2 新增 |
| ✅ | AWS Bedrock | Claude on AWS | - | v0.3 新增 |
| ✅ | Moonshot | 月之暗面 | - | v0.3 新增 (中國) |
| ⬜ | Minimax | - | 🟢 低 | 中國市場 |
| ✅ | GLM (智譜) | ChatGLM | - | v0.3 新增 (中國) |

### 待辦事項

- [x] 實現 AWS Bedrock Provider
- [x] 實現 Moonshot 提供者
- [x] 實現 GLM (智譜) 提供者
- [ ] 評估 Minimax 需求

---

## 3. 核心功能

**完成度**: 100% (12/12)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | Agent Loop | AI 代理執行循環 | - | 已完成 |
| ✅ | Memory | 記憶系統 | - | 已完成 |
| ✅ | Skills | 技能系統 | - | 已完成 |
| ✅ | Context | 對話上下文 | - | 已完成 |
| ✅ | Session | 會話管理 | - | v0.2 增強 |
| ✅ | Scheduler | 排程任務 | - | 已完成 |
| ✅ | Webhook | 事件觸發 | - | 已完成 |
| ✅ | Approvals | 審批系統 | - | 已完成 |
| ✅ | Token Tracking | Token 使用追蹤 | - | v0.2 新增 |
| ✅ | Timezone | 時區支援 | - | 已完成 |
| ✅ | Compaction | 對話壓縮 | - | v0.3 新增 |
| ✅ | Session Pruning | 會話清理 | - | v0.3 新增 |

### 待辦事項

- [ ] 實現對話 Compaction 壓縮功能
- [ ] 增強 Session Pruning 策略
- [ ] 添加自動清理過期會話

---

## 4. 群組功能

**完成度**: 100% (7/7)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | 群組聊天 | 基本群組支援 | - | 已完成 |
| ✅ | @提及觸發 | @bot 觸發回應 | - | v0.2 新增 |
| ✅ | 群組隔離 | 獨立 Session | - | v0.2 新增 |
| ✅ | 廣播訊息 | 多用戶通知 | - | v0.2 新增 |
| ✅ | 群組權限 | 權限控制 | - | v0.3 新增 |
| ✅ | Channel Routing | 頻道路由 | - | v0.3 新增 |
| ✅ | Presence | 在線狀態 | - | v0.3 新增 |

### 待辦事項

- [ ] 實現群組管理員權限
- [ ] 實現群組白名單功能
- [ ] 添加 Channel Routing 支援
- [ ] 實現 Presence 狀態顯示

---

## 5. 工具與代理

**完成度**: 100% (16/16)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | Browser | Playwright 自動化 | - | 已完成 |
| ✅ | File Operations | 檔案操作 | - | 已完成 |
| ✅ | Terminal Exec | 終端執行 | - | 已完成 |
| ✅ | Web Fetch | 網頁抓取 | - | 已完成 |
| ✅ | Multi-Agent Routing | 多代理路由 | - | v0.2 新增 |
| ✅ | Slash Commands | 斜線指令 | - | 已完成 |
| ✅ | Code Analysis | 程式碼分析 | - | Agent Skill |
| ✅ | Web Search | 網路搜尋 | - | Agent Skill |
| ✅ | Chrome Extension | 瀏覽器擴展 | - | v0.3 新增 |
| ✅ | Sandbox | 沙盒執行 | - | v0.3 新增 |
| ✅ | Subagents | 子代理 | - | v0.3 新增 |
| ✅ | LLM Task | LLM 任務工具 | - | v0.3 新增 |
| ✅ | Apply Patch | 應用補丁 | - | v0.3 新增 |
| ✅ | Agent Send | 代理發送 | - | v0.3 新增 |
| ✅ | Reactions | 表情回應 | - | v0.3 新增 |
| ✅ | Thinking Mode | 思考模式 | - | v0.3 新增 |

### 待辦事項

- [x] 實現 Sandbox 沙盒執行環境
- [x] 實現 Subagents 子代理系統
- [x] 實現 Thinking Mode 支援 Claude 思考
- [x] 添加 Reactions 表情回應功能
- [x] 實現 Apply Patch 功能
- [x] 實現 Chrome Extension

---

## 6. 媒體支援

**完成度**: 80% (8/10)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | 圖片發送/接收 | 圖片處理 | - | 已完成 |
| ✅ | 語音訊息 | 語音輸入 | - | 已完成 |
| ✅ | 語音轉錄 | Whisper | - | 已完成 |
| ✅ | 文件附件 | 文件處理 | - | 已完成 |
| ✅ | Markdown | 格式化輸出 | - | 已完成 |
| ✅ | Voice Wake | 語音喚醒 | - | v0.3 新增 |
| ⬜ | Voice Call | 語音通話 | 🟢 低 | 即時通話 |
| ✅ | Talk (TTS) | 語音輸出 | - | v0.3 新增 |
| ⬜ | Camera | 相機整合 | 🟢 低 | 即時拍照 |
| ✅ | Location | 位置分享 | - | v0.3 新增 |

### 待辦事項

- [ ] 實現 TTS 語音輸出
- [ ] 實現 Voice Wake 語音喚醒
- [ ] 添加 Location 位置分享功能
- [ ] 評估 Voice Call 需求

---

## 7. 串流與格式

**完成度**: 100% (5/5)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | Streaming | 串流回應 | - | v0.2 新增 |
| ✅ | Typing Indicator | 輸入指示 | - | v0.2 新增 |
| ✅ | Markdown | 格式化 | - | 已完成 |
| ✅ | Chunking | 分塊傳輸 | - | v0.3 新增 |
| ✅ | Draft Streaming | 草稿串流 | - | v0.3 新增 |

### 待辦事項

- [ ] 增強 Chunking 分塊邏輯
- [ ] 實現 Telegram Draft Streaming
- [ ] 優化長訊息分割

---

## 8. 網路與架構

**完成度**: 56% (5/9)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | Gateway | 統一閘道 | - | v0.3 新增 |
| ⬜ | Bridge Protocol | 橋接協議 | 🟢 低 | 跨平台 |
| ⬜ | Pairing | 設備配對 | 🟢 低 | 多設備 |
| ✅ | WebSocket | 即時通訊 | - | v0.3 新增 |
| ⬜ | Multiple Gateways | 多閘道 | 🟢 低 | 高可用 |
| ⬜ | Discovery | 服務發現 | 🟢 低 | 自動發現 |
| ⬜ | Bonjour | mDNS | 🟢 低 | 區網發現 |
| ✅ | Tailscale | VPN 整合 | - | v0.3 新增 |
| ✅ | Remote Gateway | 遠端閘道 | - | v0.3 新增 |

### 待辦事項

- [x] 設計 Gateway 架構
- [x] 實現 WebSocket 支援
- [x] 評估 Tailscale 整合需求

---

## 9. 介面與管理

**完成度**: 50% (5/10)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | Web Dashboard | 網頁儀表板 | - | v0.3 新增 |
| ✅ | Control UI | 控制介面 | - | v0.3 新增 |
| ✅ | WebChat | 網頁聊天 | - | v0.3 新增 |
| ✅ | TUI | 終端介面 | - | v0.3 新增 |
| ⬜ | Canvas | 畫布功能 | 🟢 低 | 視覺化 |
| ⬜ | macOS App | 桌面應用 | 🟢 低 | 原生應用 |
| ⬜ | iOS App | 手機應用 | 🟢 低 | 原生應用 |
| ⬜ | Android App | 手機應用 | 🟢 低 | 原生應用 |
| ✅ | Menu Bar | 選單列 | - | v0.3 新增 (macOS) |
| ⬜ | Voice Overlay | 語音覆蓋 | 🟢 低 | 語音操作 |

### 待辦事項

- [ ] 設計 Web Dashboard 架構 (React/Vue)
- [ ] 實現基本 Control UI
- [ ] 實現 WebChat 網頁版
- [ ] 評估原生應用需求

---

## 10. 安全與認證

**完成度**: 100% (6/6)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | 用戶白名單 | 授權用戶 | - | 已完成 |
| ✅ | Tool Policy | 工具策略 | - | v0.3 新增 |
| ✅ | OAuth | OAuth 認證 | - | v0.3 新增 |
| ✅ | Gateway Token | 閘道令牌 | - | v0.3 新增 |
| ✅ | Gateway Lock | 閘道鎖定 | - | v0.3 新增 |
| ✅ | Sandbox Security | 沙盒安全 | - | v0.3 新增 |
| ✅ | Elevated | 權限提升 | - | v0.3 新增 |

### 待辦事項

- [ ] 實現 OAuth 2.0 認證
- [ ] 實現 API Token 機制
- [ ] 增強 Tool Policy 控制
- [ ] 實現 Sandbox 安全隔離

---

## 11. 運維與監控

**完成度**: 100% (6/6)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | Health Check | 健康檢查 | - | v0.2 增強 |
| ✅ | Logging | 日誌記錄 | - | 已完成 |
| ✅ | Heartbeat | 心跳機制 | - | v0.3 新增 |
| ✅ | Doctor | 診斷工具 | - | v0.3 新增 |
| ✅ | Retry | 重試機制 | - | v0.3 新增 |
| ✅ | Queue | 任務佇列 | - | v0.3 新增 |

### 待辦事項

- [ ] 實現完整 Heartbeat 機制
- [ ] 增強 Doctor 診斷功能
- [ ] 優化 Retry 重試策略
- [ ] 實現任務 Queue 管理

---

## 12. 部署支援

**完成度**: 50% (5/10)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | Docker | 容器化 | - | 已完成 |
| ✅ | Docker Compose | 編排 | - | 已完成 |
| ✅ | Railway | 一鍵部署 | - | v0.3 新增 |
| ✅ | Render | 一鍵部署 | - | v0.3 新增 |
| ✅ | Fly.io | 邊緣部署 | - | v0.3 新增 |
| ⬜ | Hetzner | VPS 部署 | 🟢 低 | 歐洲託管 |
| ⬜ | GCP | 雲端部署 | 🟢 低 | Google Cloud |
| ⬜ | Nix | Nix 套件 | 🟢 低 | 可重現 |
| ⬜ | Ansible | 自動化 | 🟢 低 | 配置管理 |
| ⬜ | Bun | 替代運行時 | 🟢 低 | 效能優化 |

### 待辦事項

- [ ] 創建 Railway 部署模板
- [ ] 創建 Render 部署模板
- [ ] 編寫 Fly.io 部署指南
- [ ] 評估其他雲端平台需求

---

## 13. CLI 命令

**完成度**: 100% (10/10)

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | Status | 狀態查詢 | - | cursorbot status |
| ✅ | Logs | 日誌查看 | - | cursorbot logs |
| ✅ | Setup | 安裝設定 | - | 腳本形式 |
| ✅ | Configure | 配置管理 | - | cursorbot config |
| ✅ | Doctor | 診斷 | - | cursorbot doctor |
| ✅ | Message | 發送訊息 | - | cursorbot message |
| ✅ | Sessions | 會話管理 | - | cursorbot sessions |
| ✅ | Onboard | 引導設定 | - | cursorbot onboard |
| ✅ | Dashboard | 儀表板 | - | cursorbot dashboard |
| ✅ | Reset | 重置 | - | cursorbot reset |

### 待辦事項

- [ ] 實現 CLI 工具 `cursorbot`
- [ ] 實現互動式 Onboard 流程
- [ ] 實現 CLI Dashboard
- [ ] 添加 Reset 功能

---

## 版本規劃

### v0.2.0 (當前版本)
- ✅ Model Failover
- ✅ Usage Tracking
- ✅ @提及觸發
- ✅ Session 管理增強
- ✅ 群組隔離 Session
- ✅ Multi-Agent Routing
- ✅ 廣播訊息
- ✅ Streaming 回應
- ✅ Typing 指示器
- ✅ Health Check 增強

### v0.3.0 (當前開發中)
- [x] Compaction (對話壓縮)
- [x] Subagents (子代理系統)
- [x] Thinking Mode (Claude 思考模式)
- [x] OAuth 認證 (支援 GitHub, Google, Discord)
- [x] Sandbox 沙盒執行 (Docker/Subprocess)
- [x] TTS 語音輸出 (OpenAI, Edge TTS, ElevenLabs)
- [x] Heartbeat 心跳機制
- [x] Retry 重試機制
- [x] Queue 任務佇列
- [x] Railway/Render 部署模板
- [x] Web Dashboard
- [x] WhatsApp 支援
- [x] MS Teams 支援
- [x] Tailscale VPN 整合
- [x] Discord Voice 語音監聽
- [x] iMessage 支援 (macOS)
- [x] Chrome Extension
- [x] Moonshot AI (中國市場)
- [x] Line Bot (亞洲市場)
- [x] GLM 智譜 AI (中國市場)
- [x] macOS Menu Bar 應用

### v0.4.0 (規劃中)
- [ ] 原生應用 (iOS/Android)
- [ ] Bridge Protocol
- [ ] Voice Call 支援
- [ ] Minimax AI

### v1.0.0 (長期目標)
- [ ] 完整 Gateway 架構
- [ ] 原生應用
- [ ] 完整 CLI 工具
- [ ] 多雲部署支援

---

## 貢獻指南

如果你想幫助實現這些功能，請：

1. 在 GitHub Issues 中認領一個功能
2. Fork 專案並創建 feature branch
3. 實現功能並編寫測試
4. 提交 Pull Request

優先級說明：
- 🔴 **高優先級** - 核心功能或用戶強烈需求
- 🟡 **中優先級** - 有價值的功能增強
- 🟢 **低優先級** - 未來考慮或特定場景需求

---

## 參考資源

- [Clawdbot 官方文檔](https://docs.clawd.bot/)
- [Clawdbot GitHub](https://github.com/clawdbot/clawdbot)
- [CursorBot GitHub](https://github.com/your-repo/cursorBot)

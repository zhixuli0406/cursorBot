# CursorBot Feature Roadmap

對標 [Moltbot/Clawdbot](https://github.com/moltbot/moltbot) 的功能實作進度追蹤。

**最後更新**: 2026-01-28  
**總體完成度**: 97% (175/180)  
**目前版本**: v0.4.0  
**下一版本**: v1.0.0 (正式版)

---

## 版本策略

```
v0.3.0 (目前) ──▶ v0.4.0 (Final) ──▶ v1.0.0 (正式版)
    │                │                    │
    │                │                    └── 正式發布
    │                └── 進階功能 + 原生應用 + 品質保證
    └── 核心功能完成
```

**v0.4 目標**: 
- 進階功能：Live Canvas、macOS/iOS/Android 原生應用、Multiple Gateways、DM Pairing
- 品質保證：測試覆蓋、文件、安全審計

**v1.0 條件**: v0.4 完成 + 無 Critical Bug + 文件完整

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
14. [外部整合](#14-外部整合)
15. [RAG 知識庫](#15-rag-知識庫)
16. [Apps & Nodes](#16-apps--nodes) ← 新增
17. [進階功能](#17-進階功能) ← 新增

---

## 1. 通訊平台支援

**完成度**: 50% (7/14)

根據 [Moltbot GitHub](https://github.com/moltbot/moltbot)，支援的通訊平台：

| 狀態 | 功能 | Moltbot 實現 | CursorBot 實現 | 優先級 | 備註 |
|:----:|------|--------------|---------------|:------:|------|
| ✅ | Telegram | grammY | python-telegram-bot | - | 已完成 |
| ✅ | Discord | discord.js | discord.py | - | 已完成 |
| ✅ | WhatsApp | Baileys | whatsapp-web.js | - | v0.3 新增 |
| ✅ | iMessage | imsg CLI | AppleScript | - | v0.3 新增 (macOS) |
| ✅ | Slack | Bolt | slack_sdk | - | v0.3 新增 |
| ✅ | MS Teams | Extension | botbuilder | - | v0.3 新增 |
| ✅ | Line | - | line-bot-sdk | - | v0.3 新增 |
| ✅ | Signal | signal-cli | signal_bot.py | - | v0.3 新增 |
| ✅ | Google Chat | Chat API | google_chat_bot.py | - | v0.3 新增 |
| ⬜ | Matrix | Extension | - | 🟢 低 | 開源協議 |
| ⬜ | BlueBubbles | Extension | - | 🟢 低 | iMessage 替代 |
| ⬜ | Zalo | Extension | - | 🟢 低 | 越南市場 |
| ⬜ | Zalo Personal | Extension | - | 🟢 低 | 越南個人版 |
| ⬜ | Mattermost | Plugin | - | 🟢 低 | 開源替代 |

### 待辦事項

- [x] 研究 Baileys 庫實現 WhatsApp 整合
- [x] 實現 Slack Bot API 整合
- [x] 實現 MS Teams Bot 整合
- [x] 評估 iMessage 整合可行性
- [ ] 實現 Signal 整合 (signal-cli)
- [ ] 實現 Google Chat 整合

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

## 14. 外部整合

**完成度**: 50% (4/8)

根據 [Clawdbot 功能分析](https://grenade.tw/blog/clawdbot-ai-agent/)，以下為「開箱即用」和「進階功能」的整合需求：

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | Google Calendar | 日曆讀取/管理 | - | v0.3 新增 |
| ⬜ | Apple Calendar | macOS 日曆整合 | 🟡 中 | macOS 專用 |
| ✅ | Gmail | 郵件讀取/發送/搜尋 | - | v0.3 新增 |
| ⬜ | Outlook | 郵件整合 | 🟡 中 | 企業需求 |
| ✅ | GitHub | 倉庫管理 | - | Git 整合 |
| ⬜ | Twitter/X | 社群自動化 | 🟡 中 | API 限制多 |
| ⬜ | LinkedIn | 社群發布 | 🟢 低 | 商業用途 |
| ✅ | Notion | 筆記整合 | - | Agent Skill |

### Clawdbot 「開箱即用」功能對照

| 功能 | Clawdbot | CursorBot | 狀態 |
|------|----------|-----------|:----:|
| 文件管理 | ✅ 整理下載、尋找 PDF | ✅ File Operations | ✅ |
| 基礎調查 | ✅ 搜尋新聞、總結文章 | ✅ Web Search/Fetch | ✅ |
| 日曆讀取 | ✅ 查看日程 | ✅ Google Calendar | ✅ |
| 郵件讀取 | ✅ 讀取/搜尋郵件 | ✅ Gmail 整合 | ✅ |
| 簡單自動化 | ✅ 定時腳本、監控網站 | ✅ Scheduler/Webhook | ✅ |
| 文字處理 | ✅ 總結文檔、提取關鍵點 | ✅ Agent 能力 | ✅ |

### Clawdbot 「進階功能」對照

| 功能 | Clawdbot | CursorBot | 狀態 |
|------|----------|-----------|:----:|
| 高階郵件管理 | ✅ 自動分類、智慧過濾 | ⬜ 未實現 | ⬜ |
| 交易/市場監控 | ✅ 價格警報 | ⬜ 未實現 | ⬜ |
| 社群媒體自動化 | ✅ 多平台發布 | ⬜ 部分實現 | 🟡 |
| 複雜代碼項目 | ✅ 建立應用、管理 GitHub | ✅ Cursor Agent | ✅ |
| 自訂集成 | ✅ 透過 Skills | ✅ Skills 系統 | ✅ |

### 待辦事項

- [ ] 實現 Google Calendar 整合
- [ ] 實現 Gmail 整合 (OAuth2)
- [ ] 評估 Apple Calendar 整合可行性
- [ ] 設計郵件自動分類 Skill
- [ ] 評估 Twitter API 整合需求

---

## 15. RAG 知識庫

**完成度**: 100% (8/8)

檢索增強生成（Retrieval-Augmented Generation）系統，讓 AI 能基於用戶文件回答問題。

| 狀態 | 功能 | 說明 | 優先級 | 備註 |
|:----:|------|------|:------:|------|
| ✅ | 文件索引 | 索引 PDF/MD/Code/JSON | - | v0.3 新增 |
| ✅ | 文字分塊 | 固定/句子/段落/程式碼 | - | v0.3 新增 |
| ✅ | 向量嵌入 | OpenAI/Google/Ollama | - | v0.3 新增 |
| ✅ | 向量儲存 | ChromaDB 持久化 | - | v0.3 新增 |
| ✅ | 相似度搜尋 | Top-K 檢索 | - | v0.3 新增 |
| ✅ | 上下文增強 | RAG Query | - | v0.3 新增 |
| ✅ | 自動對話存儲 | Agent/Ask/CLI 對話存入 RAG | - | v0.3 新增 |
| ✅ | URL 索引 | 索引網頁內容 | - | v0.3 新增 |

### RAG 指令

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

### 對話自動存儲

Agent、Ask、CLI 模式的對話會自動存入 RAG，支援：
- 對話問答記憶
- 基於歷史對話的知識檢索
- 跨 session 的知識累積

---

## 16. Apps & Nodes

**完成度**: 25% (2/8)

根據 [Moltbot GitHub](https://github.com/moltbot/moltbot)，支援的原生應用和設備節點：

| 狀態 | 功能 | Moltbot 說明 | CursorBot 實現 | 優先級 | 備註 |
|:----:|------|--------------|---------------|:------:|------|
| ✅ | macOS Menu Bar | 控制面板、Voice Wake、WebChat | 基本實現 | - | v0.3 新增 |
| ⬜ | macOS App (完整) | Talk Mode overlay、debug tools、remote gateway | - | 🟡 中 | SwiftUI |
| ⬜ | iOS Node | Canvas、Voice Wake、Talk Mode、camera | - | 🟡 中 | SwiftUI |
| ⬜ | Android Node | Canvas、Talk Mode、camera、screen recording | - | 🟡 中 | Kotlin |
| ✅ | WebChat | Gateway 提供的網頁聊天 | Dashboard 內建 | - | v0.3 新增 |
| ✅ | Voice Wake | 語音喚醒 (always-on) | voice_wake.py | - | v0.3 新增 |
| ✅ | Talk Mode | 持續對話模式 | talk_mode.py | - | v0.3 新增 |
| ⬜ | Bonjour Pairing | mDNS 設備配對 | - | 🟢 低 | 區網發現 |

### Moltbot Node 功能對照

| 功能 | Moltbot | CursorBot | 狀態 |
|------|---------|-----------|:----:|
| `system.run` | 本地命令執行 | Terminal Exec | ✅ |
| `system.notify` | 系統通知 | - | ⬜ |
| `canvas.*` | 視覺工作區 | - | ⬜ |
| `camera.snap/clip` | 相機拍照/錄影 | - | ⬜ |
| `screen.record` | 螢幕錄製 | - | ⬜ |
| `location.get` | 位置取得 | Location Skill | ✅ |
| `node.invoke` | 設備節點調用 | - | ⬜ |

### 待辦事項

- [ ] 評估 SwiftUI macOS App 開發
- [ ] 評估 iOS/Android Node 架構
- [ ] 實現 Voice Wake 功能
- [ ] 實現 Talk Mode 持續對話
- [ ] 實現 system.notify 系統通知

---

## 17. 進階功能

**完成度**: 40% (6/15)

根據 [Moltbot GitHub](https://github.com/moltbot/moltbot) 的進階功能：

| 狀態 | 功能 | Moltbot 說明 | CursorBot 實現 | 優先級 | 備註 |
|:----:|------|--------------|---------------|:------:|------|
| ✅ | Agent Loop | Pi agent runtime | Agent Loop | - | 已完成 |
| ✅ | Skills Platform | bundled/managed/workspace skills | Skills 系統 | - | 已完成 |
| ✅ | Skills Registry | ClawdHub skill registry | Skills Registry | - | v0.3 新增 |
| ⬜ | Live Canvas | A2UI agent-driven workspace | - | 🟡 中 | 視覺化工作區 |
| ✅ | Browser Control | Chrome/Chromium CDP | Playwright | - | 已完成 |
| ✅ | Gmail 整合 | 郵件讀取/發送/搜尋 | Gmail Manager | - | v0.3 新增 |
| ✅ | Cron | 排程任務 | Scheduler | - | 已完成 |
| ✅ | Webhooks | 事件觸發 | Webhook | - | 已完成 |
| ✅ | Agent to Agent | sessions_* tools 跨 session 協作 | agent_to_agent.py | - | v0.3 新增 |
| ⬜ | DM Pairing | 設備配對碼 | - | 🟡 中 | 安全配對 |
| ⬜ | Elevated Mode | 權限提升模式 | - | 🟢 低 | /elevated on|off |
| ✅ | Model Failover | 自動切換備用模型 | Model Failover | - | v0.2 新增 |
| ⬜ | Nix Mode | 聲明式配置 | - | 🟢 低 | 可重現環境 |
| ⬜ | SSH Tunnels | 遠端訪問 | - | 🟢 低 | 內網穿透 |
| ⬜ | Multiple Gateways | 多閘道高可用 | - | 🟢 低 | HA 架構 |

### Moltbot Chat Commands 對照

| 指令 | Moltbot | CursorBot | 狀態 |
|------|---------|-----------|:----:|
| `/status` | 狀態查詢 | `/status` | ✅ |
| `/new` or `/reset` | 重置 session | `/new`, `/clear` | ✅ |
| `/compact` | 壓縮上下文 | `/compact` | ✅ |
| `/think <level>` | 思考等級 (off~xhigh) | 部分支援 | 🟡 |
| `/verbose on\|off` | 詳細模式 | - | ⬜ |
| `/usage off\|tokens\|full` | 使用量顯示 | `/stats` | ✅ |
| `/restart` | 重啟 Gateway | - | ⬜ |
| `/activation mention\|always` | 群組激活模式 | 已支援 | ✅ |
| `/elevated on\|off` | 權限提升 | - | ⬜ |

### 待辦事項

- [x] 實現 Gmail 整合（讀取/發送/搜尋）
- [x] 實現 Skills Registry (ClawdHub 風格)
- [x] 實現 Google Calendar 整合
- [x] 實現 Signal 整合
- [x] 實現 Google Chat 整合
- [x] 實現 Voice Wake 語音喚醒
- [x] 實現 Talk Mode 持續對話
- [x] 實現 Agent to Agent 跨 session 協作
- [ ] 實現 Gmail Pub/Sub 郵件觸發器
- [ ] 實現 Live Canvas (A2UI)
- [ ] 實現 DM Pairing 設備配對
- [ ] 添加 /verbose 指令
- [ ] 添加 /elevated 權限提升

---

## 版本規劃

### v0.2.0 (已發布)
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

### v0.3.0 (當前版本)
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
- [x] RAG 知識庫系統
- [x] 對話自動存儲到 RAG
- [x] GitHub Copilot / GitHub Models 整合
- [x] Google Calendar 整合
- [x] Gmail 整合（讀取/發送/搜尋）
- [x] Skills Registry（技能市集）
- [x] Signal 整合
- [x] Google Chat 整合
- [x] Voice Wake 語音喚醒
- [x] Talk Mode 持續對話
- [x] Agent to Agent 跨 session 協作

### v0.4.0 (Release Candidate) - 進入 v1.0 的最終版本

**目標**: 完成 v0.4 後即可發布 v1.0 正式版
**狀態**: ✅ 已完成 (2026-01-28)
**最新**: 異步執行成為所有模式的預設行為

#### 1. 穩定性與品質 (必須)
| 狀態 | 項目 | 說明 |
|:----:|------|------|
| ✅ | 單元測試覆蓋 | 核心模組測試覆蓋率 > 80% (tests/test_core_modules.py) |
| ✅ | 整合測試 | 端對端測試各平台指令 (tests/test_integration.py) |
| ✅ | 錯誤處理統一化 | 統一錯誤訊息格式和 i18n (errors.py) |
| ✅ | 效能優化 | 記憶體使用、回應延遲優化 |
| ⬜ | 壓力測試 | 多用戶並發測試 (v1.0 後) |
| ⬜ | Bug 修復 | 持續修復 (v1.0 後) |

#### 2. 文件與易用性 (必須)
| 狀態 | 項目 | 說明 |
|:----:|------|------|
| ✅ | 完整 API 文件 | 所有端點和參數說明 (docs/API.md) |
| ✅ | 互動式安裝引導 | `cursorbot setup` 引導式設定 (src/cli/setup.py) |
| ✅ | 平台設定教學 | 各平台 Webhook 設定圖文教學 (docs/PLATFORM_SETUP.md) |
| ✅ | 疑難排解指南 | 常見問題 FAQ (docs/FAQ.md) |
| ✅ | CHANGELOG | 完整版本變更記錄 |
| ✅ | 貢獻指南 | CONTRIBUTING.md |

#### 3. 核心功能補齊 (必須)
| 狀態 | 項目 | 說明 |
|:----:|------|------|
| ✅ | /verbose 指令 | 詳細輸出模式 off/low/medium/high |
| ✅ | /elevated 權限提升 | 敏感操作確認機制 (time-limited) |
| ✅ | /think 指令完善 | 思考等級 off/low/medium/high/xhigh |
| ✅ | 系統通知 | 桌面推播通知 (macOS/Windows/Linux) |
| ✅ | 指令別名系統 | 用戶自訂指令別名 (system + user aliases) |

#### 4. 安全性 (必須)
| 狀態 | 項目 | 說明 |
|:----:|------|------|
| ✅ | 安全審計 | 程式碼安全掃描 (scripts/security_audit.py) |
| ✅ | 敏感資料處理 | 日誌脫敏 (API keys, tokens, passwords) |
| ✅ | Rate Limiting | Token bucket 演算法 (requests, tokens, commands) |
| ✅ | 輸入驗證 | Command injection, Path traversal, XSS 防護 |
| ✅ | 權限最小化 | 各平台最小權限原則 (permissions_minimal.py) |

#### 5. 部署與運維 (必須)
| 狀態 | 項目 | 說明 |
|:----:|------|------|
| ✅ | Docker 映像優化 | 多階段建構 (Multi-stage build) |
| ✅ | 一鍵部署腳本優化 | Railway/Render/Fly.io 模板 (docs/DEPLOYMENT.md) |
| ✅ | 環境變數驗證 | 啟動時檢查必要設定 (format, pattern) |
| ✅ | 健康檢查端點 | /health, /ready 端點 |
| ✅ | Graceful Shutdown | 優雅關閉處理 (signal handlers) |

#### 6. 進階功能 (Apps & Architecture)
| 狀態 | 項目 | 說明 | 技術 |
|:----:|------|------|------|
| ✅ | Live Canvas (A2UI) | Agent 驅動的視覺化工作區 | Python/WebSocket |
| ✅ | macOS App 完整版 | Talk Mode、Debug Tools、Remote Gateway | SwiftUI |
| ✅ | iOS Node | Canvas、Voice Wake、Talk Mode、Camera | SwiftUI |
| ✅ | Android Node | Canvas、Talk Mode、Camera、Screen Recording | Kotlin |
| ✅ | Multiple Gateways | 多閘道高可用架構 (multi_gateway.py) | Load Balancer |
| ✅ | DM Pairing | 設備配對碼機制 (dm_pairing.py) | QR Code |

#### 7. 可選功能 (Nice to Have)
| 狀態 | 項目 | 說明 | 優先級 |
|:----:|------|------|:------:|
| ✅ | 郵件自動分類 Skill | Gmail 智慧過濾 (email_classifier.py) | 🟡 中 |
| ✅ | Apple Calendar 整合 | macOS 日曆 (apple_calendar.py) | 🟢 低 |
| ✅ | Minimax AI | 中國 AI 市場 (llm_providers.py) | 🟢 低 |
| ✅ | 多語系支援 | 繁中/簡中/英文/日文 (i18n.py) | 🟡 中 |

### v1.0.0 (正式版)

**v0.4 完成後，經過最終測試即可發布 v1.0**

包含功能：
- ✅ 9+ 通訊平台支援（Telegram、Discord、LINE、Slack、WhatsApp、Teams、Google Chat、Signal、iMessage）
- ✅ 10+ AI 模型提供者（OpenAI、Claude、Gemini、OpenRouter、Ollama、Moonshot、GLM、Minimax 等）
- ✅ 完整 Cursor CLI 整合
- ✅ Agent Loop 自主代理
- ✅ SkillsMP 技能市集
- ✅ RAG 知識庫
- ✅ TUI 終端介面
- ✅ Web Dashboard
- ✅ Docker 部署
- ✅ 完整文件
- ✅ Live Canvas (A2UI) 視覺工作區
- ✅ macOS App 完整版 (apps/macos)
- ✅ iOS Node (apps/ios)
- ✅ Android Node (apps/android)
- ✅ Multiple Gateways 高可用
- ✅ DM Pairing 設備配對
- ✅ v0.4 核心指令 (verbose, think, elevated, alias, notify)

### v1.1.0 - 智慧語音助手 (Voice Assistant)

**目標：讓 CursorBot 成為像 Siri 一樣的個人語音助手**

#### 1. 進階語音喚醒 (Advanced Voice Wake)
| 狀態 | 項目 | 說明 | 難度 |
|:----:|------|------|:----:|
| ✅ | 多喚醒詞支援 | 自訂多個喚醒詞（如「嘿 Cursor」「小助手」） | 🟡 中 |
| ✅ | 聲紋識別 | 只回應特定用戶的語音 | 🔴 高 |
| ✅ | 離線喚醒 | 使用 Vosk/Porcupine 本地偵測，無需網路 | 🟡 中 |
| ✅ | 喚醒音效 | 喚醒成功/失敗的音效回饋 | 🟢 低 |
| ✅ | 環境噪音過濾 | 使用 RNNoise/WebRTC VAD 過濾背景噪音 | 🟡 中 |

#### 2. 自然語言意圖識別 (Intent Recognition)
| 狀態 | 項目 | 說明 | 難度 |
|:----:|------|------|:----:|
| ✅ | 意圖分類器 | 識別用戶意圖（提問、執行、控制、查詢） | 🟡 中 |
| ✅ | 實體抽取 | 抽取時間、地點、人物、數字等關鍵資訊 | 🟡 中 |
| ✅ | 槽位填充 | 多輪對話補充缺失資訊 | 🟡 中 |
| ✅ | 上下文理解 | 理解代詞指代（「它」「這個」「剛才那個」） | 🔴 高 |
| ✅ | 多語言意圖 | 支援中英日混合語音指令 | 🔴 高 |

#### 3. 語音指令系統 (Voice Commands)
| 狀態 | 項目 | 說明 | 難度 |
|:----:|------|------|:----:|
| ✅ | 系統控制 | 「打開設定」「調高音量」「截圖」 | 🟡 中 |
| ✅ | 應用啟動 | 「打開 Cursor」「啟動 VSCode」 | 🟢 低 |
| ✅ | 檔案操作 | 「新建檔案」「刪除這個」「重新命名」 | 🟡 中 |
| ✅ | 程式碼操作 | 「執行測試」「Git 提交」「建置專案」 | 🟡 中 |
| ✅ | 網頁控制 | 「打開 Google」「搜尋天氣」「播放音樂」 | 🟡 中 |
| ✅ | 智慧家居 | HomeKit/Google Home/小米 IoT 整合 | 🔴 高 |

#### 4. 智慧回應系統 (Smart Response)
| 狀態 | 項目 | 說明 | 難度 |
|:----:|------|------|:----:|
| ✅ | 自然語音合成 | 使用 ElevenLabs/Azure TTS 自然發音 | 🟡 中 |
| ✅ | 情緒語調 | 根據內容調整語調（高興、嚴肅、疑問） | 🔴 高 |
| ✅ | 語音中斷 | 說話時可被打斷，立即回應新指令 | 🟡 中 |
| ✅ | 回應長度控制 | 自動判斷簡短回覆或詳細解釋 | 🟢 低 |
| ✅ | 多語言回應 | 根據用戶語言自動切換回應語言 | 🟡 中 |

#### 5. 情境感知 (Context Awareness)
| 狀態 | 項目 | 說明 | 難度 |
|:----:|------|------|:----:|
| ✅ | 時間感知 | 「早安」「晚安」根據時間自動問候 | 🟢 低 |
| ✅ | 位置感知 | 「到家了」「在公司」觸發不同設定 | 🟡 中 |
| ✅ | 日曆整合 | 「我下午有什麼會議」「明天的行程」 | 🟡 中 |
| ✅ | 天氣整合 | 「今天需要帶傘嗎」「週末天氣如何」 | 🟢 低 |
| ✅ | 習慣學習 | 學習用戶日常習慣並主動提醒 | 🔴 高 |
| ✅ | 當前應用感知 | 根據正在使用的應用調整回應 | 🟡 中 |

#### 6. 深度系統整合 (System Integration)
| 狀態 | 項目 | 說明 | 難度 |
|:----:|------|------|:----:|
| ✅ | macOS Shortcuts | 與 Apple Shortcuts 雙向整合 | 🟡 中 |
| ✅ | iOS Shortcuts | Siri Shortcuts Intent 支援 | 🔴 高 |
| ✅ | Android Intents | Intent 系統整合 | 🟡 中 |
| ✅ | 系統通知互動 | 讀取並回應系統通知 | 🔴 高 |
| ✅ | 剪貼簿整合 | 「複製這個」「貼上剛才的」 | 🟢 低 |
| ⬜ | 螢幕內容理解 | 「這是什麼」理解螢幕上的內容 | 🔴 高 |

#### 7. 對話管理 (Conversation Management)
| 狀態 | 項目 | 說明 | 難度 |
|:----:|------|------|:----:|
| ✅ | 多輪對話 | 支援連續多輪對話，保持上下文 | 🟡 中 |
| ✅ | 對話修正 | 「不對，我是說...」修正前一個指令 | 🟡 中 |
| ✅ | 確認機制 | 敏感操作前語音確認「確定要刪除嗎？」 | 🟢 低 |
| ✅ | 對話歷史 | 「剛才我問了什麼」回顧對話 | 🟢 低 |
| ✅ | 對話摘要 | 長對話自動生成摘要 | 🟡 中 |

#### 8. 個人化與學習 (Personalization)
| 狀態 | 項目 | 說明 | 難度 |
|:----:|------|------|:----:|
| ✅ | 用戶偏好學習 | 記住用戶的習慣和偏好 | 🟡 中 |
| ✅ | 常用指令預測 | 根據時間/情境預測可能的指令 | 🔴 高 |
| ✅ | 個人詞彙表 | 學習用戶的專有名詞和縮寫 | 🟡 中 |
| ✅ | 回應風格調整 | 正式/輕鬆/技術風格切換 | 🟢 低 |
| ✅ | 隱私控制 | 用戶可控制哪些資料被記住 | 🟡 中 |

#### 9. 離線能力 (Offline Capabilities)
| 狀態 | 項目 | 說明 | 難度 |
|:----:|------|------|:----:|
| ✅ | 離線語音辨識 | Vosk/Whisper.cpp 本地辨識 | 🟡 中 |
| ✅ | 離線 TTS | Piper/eSpeak 本地語音合成 | 🟡 中 |
| ✅ | 離線意圖識別 | 本地小型 NLU 模型 | 🔴 高 |
| ✅ | 離線指令執行 | 基本系統控制指令離線可用 | 🟡 中 |
| ✅ | 自動切換 | 網路斷線時自動切換離線模式 | 🟢 低 |

#### 10. 進階功能 (Advanced Features)
| 狀態 | 項目 | 說明 | 難度 |
|:----:|------|------|:----:|
| ✅ | 即時翻譯 | 語音輸入即時翻譯並朗讀 | 🟡 中 |
| ✅ | 會議助手 | 會議錄音、摘要、行動項目提取 | 🔴 高 |
| ✅ | 語音備忘錄 | 「記住這個」「提醒我明天...」 | 🟢 低 |
| ✅ | 語音搜尋 | 在檔案/程式碼/筆記中語音搜尋 | 🟡 中 |
| ✅ | 語音導航 | 在 IDE 中語音導航「跳到第 50 行」 | 🟡 中 |
| ✅ | 無障礙支援 | 為視障用戶優化的完整語音操作 | 🔴 高 |

#### v1.1 技術架構

```
┌─────────────────────────────────────────────────────────────┐
│                    CursorBot v1.1 語音架構                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Voice Wake  │──│    STT      │──│   Intent    │         │
│  │ (Porcupine) │  │(Whisper/云) │  │  Recognition│         │
│  └─────────────┘  └─────────────┘  └──────┬──────┘         │
│                                           │                 │
│  ┌─────────────────────────────────────────┘                │
│  │                                                          │
│  ▼                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Context   │──│   Action    │──│    TTS      │         │
│  │   Manager   │  │   Executor  │  │ (ElevenLabs)│         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│        │                │                                   │
│        ▼                ▼                                   │
│  ┌─────────────┐  ┌─────────────┐                          │
│  │  Memory &   │  │   System    │                          │
│  │ Preferences │  │ Integration │                          │
│  └─────────────┘  └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

#### v1.1 里程碑

| 階段 | 內容 | 目標 | 狀態 |
|------|------|------|:----:|
| Phase 1 | 進階語音喚醒 + 離線辨識 | 可靠的語音輸入 | ✅ 已完成 |
| Phase 2 | 意圖識別 + 語音指令 | 聲控基本操作 | ✅ 已完成 |
| Phase 3 | 情境感知 + 系統整合 | 智慧化互動 | ✅ 已完成 |
| Phase 4 | 個人化學習 + 進階功能 | 真正的個人助手 | ✅ 已完成 |

#### v1.1 核心模組實作

| 模組 | 檔案 | 功能 |
|------|------|------|
| 語音助手核心 | `src/core/voice_assistant.py` | 多引擎 STT/TTS、喚醒詞偵測、VAD、噪音過濾 |
| 語音指令系統 | `src/core/voice_commands.py` | 系統控制、應用程式、Git、網頁搜尋、提醒 |
| 情境感知引擎 | `src/core/voice_context.py` | 時間/地點/活動/裝置情境、個人化建議 |
| LLM 整合 | `src/core/voice_llm.py` | 自然對話、情境回應、意圖分析 |
| 個人化學習 | `src/core/voice_learning.py` | 使用模式學習、快捷指令、偏好適應 |
| 槽位填充 | `src/core/voice_slots.py` | 多輪對話補充、實體抽取、對話狀態管理 |
| 擴展整合 | `src/core/voice_integrations.py` | 檔案操作、剪貼簿、天氣、日曆、翻譯、搜尋 |
| 進階功能 | `src/core/voice_advanced.py` | 聲紋識別、情緒 TTS、會議助手、語音導航、智慧家居 |
| 個人秘書 | `src/core/secretary.py` | 每日簡報、待辦管理、訂票助手、秘書人設 |

#### v1.1 個人秘書功能

| 狀態 | 項目 | 說明 |
|:----:|------|------|
| ✅ | 每日簡報 | 自動發送今日行程、待辦事項、關懷訊息 |
| ✅ | 待辦事項管理 | 新增/完成/刪除待辦，支援優先級設定 |
| ✅ | 行程整合 | Google Calendar + Apple Calendar 整合 |
| ✅ | 訂票助手 | 機票/火車票/飯店預訂協助 |
| ✅ | 秘書人設 | 可自訂名稱，女秘書親切對話風格 |
| ✅ | 時間感知 | 根據時段自動調整問候語與關懷訊息 |

**秘書指令：**
```
/briefing         - 今日簡報
/todo add <任務>  - 新增待辦
/todo done <編號> - 完成待辦
/book flight      - 機票預訂協助
/book train       - 火車票預訂
/book hotel       - 飯店預訂
/secretary        - 秘書設定
/secretary name   - 設定您的稱呼
/secretary rename - 修改秘書名稱
```

### 未來版本 (v1.x Post-Release)

以下功能移至 v1.1 後的迭代版本：

| 版本 | 功能 | 說明 |
|------|------|------|
| v1.2 | 多設備協作 | 手機、電腦、平板無縫切換 |
| v1.2 | AR/VR 支援 | Vision Pro / Quest 整合 |
| v1.2 | 車載模式 | CarPlay / Android Auto 整合 |
| v1.x | Matrix 協議 | 開源通訊協議 |
| v1.x | Nix Mode | 聲明式配置 |
| v1.x | SSH Tunnels | 內網穿透 |
| v1.x | Bonjour Discovery | mDNS 區網發現 |

---

## Moltbot 功能差距總結

根據 [Moltbot GitHub](https://github.com/moltbot/moltbot) 分析：

### ✅ 已完成的核心功能
| 功能 | 說明 | 版本 |
|------|------|:----:|
| 多平台通訊 | Telegram/Discord/LINE/Slack/WhatsApp/Teams/Google Chat | v0.3 |
| 多 AI 提供者 | OpenAI/Claude/Gemini/OpenRouter/Ollama | v0.3 |
| Gmail 整合 | 郵件讀取/發送/搜尋 | v0.3 |
| Google Calendar | 日曆讀取/管理/新增 | v0.3 |
| Skills Registry | SkillsMP 技能市集整合 | v0.3 |
| RAG 知識庫 | 文件索引/向量搜尋 | v0.3 |
| Agent Loop | 自主代理執行 | v0.3 |
| Voice Wake | 語音喚醒 | v0.3 |
| Talk Mode | 持續對話模式 | v0.3 |
| Agent to Agent | 跨 session 協作 | v0.3 |

### 🎯 v0.4 需完成（進入 v1.0 的條件）

#### 基礎建設
| 功能 | 說明 | 類型 |
|------|------|:----:|
| 測試覆蓋 | 單元測試 + 整合測試 | 品質 |
| 完整文件 | API 文件 + 教學 + FAQ | 文件 |
| 安全審計 | 程式碼掃描 + 敏感資料處理 | 安全 |
| /verbose | 詳細輸出模式 | 功能 |
| /elevated | 權限提升機制 | 功能 |
| 系統通知 | 桌面推播 | 功能 |

#### 進階功能
| 功能 | 說明 | 難度 |
|------|------|:----:|
| Live Canvas (A2UI) | Agent 驅動的視覺工作區 | 高 |
| macOS App 完整版 | SwiftUI 原生應用 | 高 |
| iOS Node | iOS 設備節點 | 高 |
| Android Node | Android 設備節點 | 高 |
| Multiple Gateways | 高可用架構 | 中 |
| DM Pairing | 設備配對機制 | 中 |

### 📦 v1.x 後續迭代
| 功能 | 說明 | 難度 |
|------|------|:----:|
| Matrix | 開源協議 | 中 |
| Nix Mode | 聲明式配置 | 低 |
| SSH Tunnels | 內網穿透 | 低 |

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

- [Moltbot/Clawdbot GitHub](https://github.com/moltbot/moltbot)
- [Moltbot 官方網站](https://molt.bot)
- [Clawdbot 文檔](https://docs.clawd.bot/)
- [Clawdbot 終極指南](https://grenade.tw/blog/clawdbot-ai-agent/)
- [CursorBot GitHub](https://github.com/your-repo/cursorBot)

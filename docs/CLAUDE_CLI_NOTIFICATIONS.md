# Claude Code CLI 任務完成通知系統

## 📋 概述

ClaudeBot v2.0+ 支援監控本地 Claude Code CLI 任務執行，並在任務完成時自動發送通知到 Telegram/Discord。

透過監控 `~/.claude/` 目錄，系統能夠即時檢測任務狀態變化，實現無縫的桌面-移動端工作流。

## ✨ 功能特點

### 🔔 實時通知
- 自動檢測 Claude Code CLI 任務完成
- 支援多平台通知 (Telegram, Discord)
- 詳細的任務執行報告
- 執行時長統計

### 📊 任務管理
- 查看運行中的任務
- 瀏覽已完成的任務
- 查看任務詳細信息
- 任務輸出預覽

### 🎯 智能識別
- 自動解析 JSON 狀態文件
- 日誌文件完成標記檢測
- 輸出文件關聯
- 任務生命週期追蹤

## 🚀 快速開始

### 1. 啟用通知

在 Telegram 中發送命令：

```
/claude_notify on
```

回應：
```
✅ Claude Code CLI 通知已啟用

當您在電腦端執行的 Claude Code CLI 任務完成時，
我會自動發送通知到這個聊天。

監控目錄: ~/.claude/
```

### 2. 在電腦端執行任務

使用 Claude Code CLI 執行任務：

```bash
# 例如：讓 Claude 幫你寫代碼
claude chat "幫我寫一個 Python 爬蟲"

# 或使用 Ask 模式
claude ask "這段代碼是做什麼的？"
```

### 3. 接收通知

當任務完成時，ClaudeBot 會自動發送通知：

```
✅ Claude Code CLI 任務完成

任務ID: chat-2026-02-10-12345
狀態: completed
執行時長: 45.3秒

輸出:
```python
import requests
from bs4 import BeautifulSoup
...
```

⏰ 2026-02-10 12:34:56
```

## 📝 可用命令

### /claude_notify [on|off|status]

管理 Claude CLI 通知設定

**參數：**
- `on` - 啟用通知 (默認)
- `off` - 停用通知
- `status` - 查看當前狀態

**範例：**

```
/claude_notify on      # 啟用通知
/claude_notify off     # 停用通知
/claude_notify status  # 查看狀態
```

**狀態輸出：**
```
📊 Claude CLI 通知狀態

通知狀態: ✅ 已啟用
監控目錄: ~/.claude/
運行中任務: 2
已完成任務: 15

運行中的任務:
• chat-12345 (已運行 30秒)
• ask-67890 (已運行 15秒)
```

### /claude_tasks [running|completed|all]

查看 Claude Code CLI 任務列表

**參數：**
- `running` - 僅顯示運行中的任務
- `completed` - 僅顯示已完成的任務
- `all` - 顯示所有任務 (默認)

**範例：**

```
/claude_tasks           # 顯示所有任務
/claude_tasks running   # 僅運行中
/claude_tasks completed # 僅已完成
```

**輸出範例：**
```
🏃 運行中的任務

1. 🏃 chat-2026-02-10-12345
   狀態: running | 時長: 進行中

2. ✅ ask-2026-02-10-67890
   狀態: completed | 時長: 45秒

3. ❌ edit-2026-02-10-54321
   狀態: failed | 時長: 10秒
   ⚠️ 錯誤: Connection timeout...
```

### /claude_task <task_id>

查看任務詳細信息

**參數：**
- `task_id` - 任務 ID (從 `/claude_tasks` 獲取)

**範例：**

```
/claude_task chat-2026-02-10-12345
```

**輸出範例：**
```
✅ 任務詳情

ID: chat-2026-02-10-12345
狀態: completed
執行時長: 45.3秒
用戶: 5581530676

元數據:
• model: claude-sonnet-4.5
• tokens: 2500

輸出:
```python
import requests
from bs4 import BeautifulSoup

def scrape_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.find_all('div', class_='content')

# 使用範例
url = "https://example.com"
content = scrape_website(url)
print(content)
```
```

## 🔧 技術實現

### 架構組件

```
┌─────────────────────────────────────────┐
│    ~/.claude/ 目錄                       │
│  ├── tasks/                             │
│  │   └── *.json (任務狀態)              │
│  ├── sessions/                          │
│  │   └── *.json (會話信息)              │
│  └── output/                            │
│      └── *.txt/*.md (任務輸出)          │
└─────────────────────────────────────────┘
            ↓ (Watchdog 監控)
┌─────────────────────────────────────────┐
│  ClaudeCliMonitor (監控器)               │
│  ├── 文件系統事件監聽                     │
│  ├── JSON/Log 解析                       │
│  ├── 任務狀態追蹤                        │
│  └── 完成檢測邏輯                        │
└─────────────────────────────────────────┘
            ↓ (任務完成回調)
┌─────────────────────────────────────────┐
│  ClaudeCliNotifier (通知器)              │
│  ├── 用戶平台映射                        │
│  ├── 消息格式化                          │
│  └── 多平台消息分發                      │
└─────────────────────────────────────────┘
            ↓ (發送通知)
┌─────────────────────────────────────────┐
│  Telegram / Discord Bot                  │
│  └── 發送格式化通知到用戶聊天             │
└─────────────────────────────────────────┘
```

### 核心模組

#### 1. ClaudeCliMonitor (監控器)

**位置**: `src/integrations/claude_cli_monitor.py`

**職責**:
- 使用 Watchdog 監控 `~/.claude/` 目錄
- 解析 JSON 狀態文件、日誌文件、輸出文件
- 追蹤任務生命週期 (running → completed/failed)
- 觸發任務完成回調

**關鍵類**:
```python
class ClaudeTask:
    """任務模型"""
    task_id: str
    status: str  # running, completed, failed
    start_time: float
    end_time: Optional[float]
    output: str
    error: Optional[str]
    duration: Optional[float]

class ClaudeCliMonitor:
    """監控器"""
    async def start()  # 啟動監控
    async def stop()   # 停止監控
    async def handle_file_change()  # 處理文件變化
```

**檢測邏輯**:
1. **JSON 文件**: 解析 `status` 欄位，檢測 `completed`/`failed`/`done`/`error`
2. **日誌文件**: 搜索完成標記關鍵詞
3. **輸出文件**: 關聯到任務 ID

#### 2. ClaudeCliNotifier (通知器)

**位置**: `src/integrations/claude_cli_notifier.py`

**職責**:
- 管理用戶平台映射 (user_id → platform, chat_id)
- 格式化通知消息
- 分發到不同平台 (Telegram, Discord)

**關鍵方法**:
```python
class ClaudeCliNotifier:
    def register_user(user_id, platform, chat_id)
    async def send_notification(task, message)
    async def _send_telegram_notification()
    async def _send_discord_notification()
```

#### 3. Command Handlers (命令處理器)

**位置**: `src/bot/handlers/claude_cli_handlers.py`

**職責**:
- 處理用戶命令 (`/claude_notify`, `/claude_tasks`, `/claude_task`)
- 註冊/取消註冊用戶通知
- 查詢任務列表和詳情

### 文件格式支援

#### JSON 狀態文件 (推薦)

Claude CLI 應輸出 JSON 格式的狀態文件：

```json
{
  "id": "task-12345",
  "status": "completed",
  "start_time": 1707552000.0,
  "output": "任務輸出內容...",
  "metadata": {
    "model": "claude-sonnet-4.5",
    "tokens": 2500
  }
}
```

**檢測條件**: `status` 為 `completed`, `done`, `failed`, `error`

#### 日誌文件

```
[2026-02-10 12:34:56] Task started: chat-12345
[2026-02-10 12:35:30] Processing request...
[2026-02-10 12:35:42] Task completed successfully
```

**檢測條件**: 最後 50 行中包含 `completed`, `finished`, `done`, `success`, `task complete`

#### 輸出文件

純文本或 Markdown 輸出文件會被自動關聯到對應任務。

## ⚙️ 配置

### 環境變數

無需額外配置，系統會自動使用現有的 Telegram/Discord Bot 設定。

### 監控目錄

默認監控: `~/.claude/`

可在初始化時自定義：
```python
from src.integrations.claude_cli_monitor import ClaudeCliMonitor

monitor = ClaudeCliMonitor(claude_dir="/custom/path")
```

### 通知格式

通知消息格式在 `ClaudeCliMonitor._format_notification()` 中定義，可自定義：

```python
def _format_notification(self, task: ClaudeTask) -> str:
    status_emoji = "✅" if task.status == "completed" else "❌"
    return f"{status_emoji} **任務完成**\n..."
```

## 🔒 安全性

### 用戶隔離
- 每個用戶只能看到自己註冊的任務
- 通知只發送到已註冊的用戶

### 權限控制
- 所有命令需要授權 (`@authorized_only`)
- 遵循 ClaudeBot 的用戶白名單機制

### 數據隱私
- 任務輸出僅發送給任務所有者
- 敏感信息自動截斷（最多 200/300 字元）

## 📊 性能考量

### 文件監控
- 使用 Watchdog 高效的事件驅動機制
- 僅監控相關目錄 (`tasks/`, `sessions/`, `output/`)
- 自動過濾不相關事件

### 資源使用
- 異步 I/O，非阻塞
- 任務緩存在內存中
- 文件讀取按需加載

### 限制
- 最多顯示 10 個任務列表項
- 輸出預覽最多 200-300 字元
- 日誌文件僅檢查最後 50 行

## 🐛 故障排除

### 通知未收到

**問題**: 執行任務但沒收到通知

**解決方案**:
1. 確認已啟用通知: `/claude_notify status`
2. 檢查監控目錄是否正確: `~/.claude/`
3. 確認 Claude CLI 寫入狀態文件
4. 查看 ClaudeBot 日誌

### 任務未顯示

**問題**: `/claude_tasks` 沒有顯示任務

**解決方案**:
1. 確認任務文件格式正確 (JSON)
2. 檢查文件權限
3. 手動註冊任務：
   ```python
   from src.integrations.claude_cli_monitor import get_claude_cli_monitor
   monitor = get_claude_cli_monitor()
   monitor.register_task("task-id", user_id="123")
   ```

### 監控未啟動

**問題**: 監控系統未運行

**解決方案**:
1. 檢查 ClaudeBot 啟動日誌
2. 確認 watchdog 已安裝: `pip install watchdog>=3.0.0`
3. 手動啟動監控：
   ```python
   from src.integrations.claude_cli_monitor import start_claude_cli_monitor
   await start_claude_cli_monitor()
   ```

## 🔄 與 OpenClaw 的對比

| 功能 | ClaudeBot | OpenClaw |
|------|-----------|----------|
| 本地任務監控 | ✅ ~/.claude/ | ✅ ~/.openclaw/ |
| 文件系統監控 | ✅ Watchdog | ✅ 自定義監控 |
| 任務完成通知 | ✅ | ✅ |
| 多平台通知 | ✅ Telegram, Discord | ✅ 全平台 |
| 任務列表查詢 | ✅ | ✅ |
| 任務詳情查看 | ✅ | ✅ |
| 自動註冊 | ✅ 自動檢測 | ⚠️ 需手動 |

**優勢**:
- ✅ 更簡單的用戶體驗
- ✅ 自動任務發現
- ✅ 輕量級實現

## 📚 API 參考

### Python API

```python
# 獲取監控器實例
from src.integrations.claude_cli_monitor import get_claude_cli_monitor

monitor = get_claude_cli_monitor()

# 註冊任務
monitor.register_task(
    task_id="my-task",
    user_id="123456",
    platform="telegram",
    metadata={"model": "claude-sonnet-4.5"}
)

# 獲取任務
task = monitor.get_task("my-task")
print(f"Status: {task.status}, Duration: {task.duration}")

# 列出任務
running_tasks = monitor.list_tasks(status="running")
completed_tasks = monitor.list_tasks(status="completed")
```

```python
# 獲取通知器實例
from src.integrations.claude_cli_notifier import get_claude_cli_notifier

notifier = get_claude_cli_notifier()

# 註冊用戶
notifier.register_user(
    user_id="123456",
    platform="telegram",
    chat_id="123456"
)

# 發送自定義通知
await notifier.send_notification(task, custom_message)
```

## 🎯 最佳實踐

### 1. Claude CLI 輸出格式

推薦在 Claude CLI 腳本中輸出 JSON 狀態文件：

```python
import json
from pathlib import Path

def save_task_status(task_id, status, output):
    status_file = Path.home() / ".claude" / "tasks" / f"{task_id}.json"
    status_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "id": task_id,
        "status": status,
        "output": output,
        "start_time": start_time,
        "end_time": time.time(),
    }

    with open(status_file, "w") as f:
        json.dump(data, f)
```

### 2. 用戶體驗

- 在執行長任務前啟用通知
- 定期查看 `/claude_tasks` 瞭解任務狀態
- 使用 `/claude_task` 查看詳細輸出

### 3. 開發整合

在自動化腳本中整合：

```bash
#!/bin/bash
# start_claude_task.sh

TASK_ID="task-$(date +%s)"
echo "{\"id\": \"$TASK_ID\", \"status\": \"running\"}" > ~/.claude/tasks/$TASK_ID.json

# 執行任務
claude chat "$1" > /tmp/output.txt

# 更新狀態
echo "{\"id\": \"$TASK_ID\", \"status\": \"completed\", \"output\": \"$(cat /tmp/output.txt)\"}" > ~/.claude/tasks/$TASK_ID.json
```

## 📝 更新日誌

### v2.0.1 (2026-02-10)
- ✅ 初始實現
- ✅ Telegram 支援
- ✅ JSON/日誌文件解析
- ✅ 任務列表和詳情查詢

### 計劃中
- 🔄 Discord 完整支援
- 🔄 LINE/Slack 支援
- 🔄 任務過濾和搜索
- 🔄 任務執行統計
- 🔄 自定義通知模板

## 🤝 貢獻

歡迎貢獻！請參考 [CONTRIBUTING.md](../CONTRIBUTING.md)

## 📄 授權

MIT License - 參見 [LICENSE](../LICENSE)

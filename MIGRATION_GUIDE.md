# CursorBot → ClaudeBot 迁移指南

## 概述

本指南帮助您从 CursorBot v1.1.0 平滑迁移到 ClaudeBot v2.0.0。

**重要提示**：这是一个包含破坏性变更的主要版本升级。请仔细阅读本指南并按照步骤操作。

---

## 主要变更

### 品牌重命名
- **项目名称**：CursorBot → ClaudeBot
- **GitHub 仓库**：`zhixuli0406/cursorBot` → `zhixuli0406/claudeBot`
- **命令行工具**：`./cursorbot` → `./claudebot`

### 技术变更
- **CLI 工具**：Cursor CLI (`agent` 命令) → Claude Code CLI (`claude` 命令)
- **核心模块**：`src/cursor/` → `src/claude/`
- **环境变量**：`CURSOR_*` → `CLAUDE_*`
- **唤醒词**：'hey cursor', 'ok cursor' → 'hey claude', 'ok claude'

### 应用变更
- **Android 包名**：`com.cursorbot.node` → `com.claudebot.node`
- **iOS/macOS Bundle ID**：`com.cursorbot.*` → `com.claudebot.*`
- **数据库文件**：`cursorbot.db` → `claudebot.db`（自动迁移）
- **日志文件**：`cursorbot.log` → `claudebot.log`

---

## 前提条件

在开始迁移之前，请确保您具备：

1. **Python 3.12+**
2. **Claude API Key**（从 [Anthropic Console](https://console.anthropic.com) 获取）
3. **备份**：确保您已备份所有重要数据

---

## 迁移步骤

### 步骤 1: 安装 Claude Code CLI

ClaudeBot v2.0 使用 Claude Code CLI 替代 Cursor CLI。

#### 选项 A: 使用 pip 安装（推荐）
```bash
pip install claude-code
```

#### 选项 B: 使用安装脚本
```bash
curl -sSL https://anthropic.com/install-claude-code | bash
```

#### 验证安装
```bash
claude --version
```

如果看到版本信息，说明安装成功。

---

### 步骤 2: 备份现有配置

在进行任何更改之前，备份您的配置文件：

```bash
# 备份环境变量
cp .env .env.cursorbot.backup

# 备份数据库（如果存在）
cp cursorbot.db cursorbot.db.backup 2>/dev/null || true
```

---

### 步骤 3: 更新环境变量

#### 自动迁移（推荐）
使用我们提供的迁移脚本：

```bash
# 预览变更（不修改文件）
python scripts/migrate_env.py --dry-run

# 执行迁移
python scripts/migrate_env.py
```

#### 手动迁移
如果您更喜欢手动编辑，请更新 `.env` 文件中的以下变量：

```bash
# 旧变量名 → 新变量名
CURSOR_API_KEY           → CLAUDE_API_KEY
CURSOR_WORKSPACE_PATH    → CLAUDE_WORKSPACE_PATH
CURSOR_WORKING_DIR       → CLAUDE_WORKING_DIR
CURSOR_CLI_MODEL         → CLAUDE_CLI_MODEL
CURSOR_CLI_TIMEOUT       → CLAUDE_CLI_TIMEOUT
CURSOR_GITHUB_REPO       → CLAUDE_GITHUB_REPO
```

**重要**：`CLAUDE_API_KEY` 的值需要更新为您的 Anthropic API Key。

---

### 步骤 4: 更新 Docker 配置（如果使用 Docker）

#### 4.1 停止旧容器
```bash
docker-compose down
```

#### 4.2 清理旧镜像
```bash
docker rmi cursorbot:latest 2>/dev/null || true
```

#### 4.3 拉取最新代码
```bash
git pull origin main
# 或者
git fetch origin && git checkout v2.0.0
```

#### 4.4 重新构建并启动
```bash
docker-compose build
docker-compose up -d
```

#### 4.5 验证运行状态
```bash
docker-compose ps
docker-compose logs -f claudebot
```

---

### 步骤 5: 本地部署迁移（非 Docker）

#### 5.1 拉取最新代码
```bash
cd /path/to/cursorBot
git pull origin main
# 或者
git fetch origin && git checkout v2.0.0
```

#### 5.2 更新依赖
```bash
pip install -r requirements.txt --upgrade
```

#### 5.3 运行数据库迁移
数据库会在首次启动时自动迁移，无需手动操作。

#### 5.4 启动应用
```bash
python -m src.main
# 或者使用新的可执行文件
./claudebot tui
```

---

### 步骤 6: 原生应用迁移（Android/iOS/macOS）

**重要警告**：由于包名/Bundle ID 已更改，您需要卸载旧应用并安装新应用。

#### Android
1. 卸载旧的 CursorBot 应用
2. 从 [GitHub Releases](https://github.com/zhixuli0406/claudeBot/releases) 下载最新的 APK
3. 安装 ClaudeBot 应用
4. 重新配置您的设置（API Key、服务器地址等）

#### iOS
1. 从设备上删除 CursorBot 应用
2. 从 App Store 或 TestFlight 安装 ClaudeBot 应用
3. 重新登录和配置

#### macOS
1. 退出 CursorBot 应用
2. 将 CursorBot.app 移至废纸篓
3. 下载并安装 ClaudeBot.app
4. 首次启动时授予必要权限（麦克风、辅助功能等）
5. 重新配置快捷键和设置

---

### 步骤 7: Chrome 扩展迁移

1. 在 Chrome 扩展管理页面 (`chrome://extensions`) 中删除 CursorBot Assistant
2. 从 [Chrome Web Store](https://chrome.google.com/webstore) 安装 ClaudeBot Assistant
3. 或者从源码加载：
   ```bash
   cd chrome-extension
   # 在 Chrome 扩展管理中选择"加载已解压的扩展程序"
   # 选择 chrome-extension 目录
   ```

---

### 步骤 8: 验证迁移

#### 8.1 检查 CLI 可用性
```bash
# 检查 Claude Code CLI
claude --version

# 检查 Python 可以导入新模块
python -c "from src.claude import ClaudeCodeCLIAgent; print('✅ Import successful')"
```

#### 8.2 测试基础功能
```bash
# 启动 TUI
./claudebot tui

# 在 TUI 中测试以下命令：
/help
/status
/climodel
```

#### 8.3 测试 AI 对话
发送一条消息给 bot，验证 AI 响应正常工作。

#### 8.4 测试秘书模式
```bash
/mode assistant
/briefing
/todo add 测试待办事项
```

#### 8.5 测试语音助手（如果使用）
说出唤醒词 "hey claude" 或 "ok claude"，验证语音识别正常。

---

## 部署平台特定说明

### Railway

1. 更新环境变量：
   ```bash
   railway variables set CLAUDE_API_KEY=your_anthropic_api_key
   railway variables delete CURSOR_API_KEY
   # 更新其他 CURSOR_* 变量
   ```

2. 重新部署：
   ```bash
   railway up
   ```

3. 验证日志：
   ```bash
   railway logs
   ```

### Render

1. 在 Render Dashboard 中更新环境变量
2. 触发手动部署或等待自动部署
3. 查看部署日志确认成功

### Fly.io

1. 更新 `fly.toml` 中的应用名称
2. 设置环境变量：
   ```bash
   fly secrets set CLAUDE_API_KEY=your_anthropic_api_key
   ```
3. 部署：
   ```bash
   fly deploy
   ```

---

## 数据迁移

### 数据库自动迁移

ClaudeBot 会在首次启动时自动检测并迁移 `cursorbot.db` 到 `claudebot.db`。

如果您想手动迁移：
```bash
cp cursorbot.db claudebot.db
```

### 对话历史

对话历史存储在数据库中，会随数据库文件一起迁移。无需额外操作。

### 技能和工作流

如果您有自定义技能或工作流配置，它们应该可以无缝迁移。如果遇到问题，请检查配置文件路径是否正确。

---

## 常见问题

### Q1: Claude Code CLI 找不到命令？

**A**: 确保 Claude Code CLI 已正确安装并在 PATH 中：

```bash
which claude
# 如果没有输出，重新安装：
pip install claude-code --force-reinstall
```

### Q2: 环境变量迁移后应用无法启动？

**A**: 检查以下几点：
1. 确认 `CLAUDE_API_KEY` 已设置且有效
2. 检查是否有遗漏的环境变量
3. 查看日志文件 `claudebot.log` 获取详细错误信息

### Q3: 数据库迁移失败？

**A**: 手动复制数据库文件：
```bash
cp cursorbot.db claudebot.db
# 如果还有问题，检查文件权限
chmod 644 claudebot.db
```

### Q4: Docker 容器无法启动？

**A**:
1. 检查 Docker Compose 版本：`docker-compose --version`
2. 清理旧容器和卷：
   ```bash
   docker-compose down -v
   docker system prune -f
   ```
3. 重新构建：`docker-compose up --build -d`

### Q5: 原生应用崩溃或无法连接？

**A**:
1. 确保服务器地址正确（如果仓库 URL 已更改）
2. 检查 API Key 是否正确
3. 重新安装应用（完全卸载后再安装）
4. 查看应用日志获取详细信息

### Q6: 语音助手无法识别新的唤醒词？

**A**:
1. 重新训练语音模型（如果使用自定义模型）
2. 确保麦克风权限已授予
3. 在设置中手动更新唤醒词配置

### Q7: Chrome 扩展无法连接到后端？

**A**:
1. 更新扩展中的服务器地址配置
2. 检查后端服务是否正常运行
3. 查看浏览器控制台的错误信息

---

## 回滚到 v1.1.0

如果迁移过程中遇到无法解决的问题，您可以回滚到旧版本：

### Docker 回滚
```bash
docker-compose down
git checkout backup-before-refactor
cp .env.cursorbot.backup .env
docker-compose up -d
```

### 本地部署回滚
```bash
git checkout backup-before-refactor
cp .env.cursorbot.backup .env
cp cursorbot.db.backup cursorbot.db
python -m src.main
```

---

## 获取帮助

如果您在迁移过程中遇到问题：

1. **查看文档**：阅读 [README.md](README.md) 和 [FAQ.md](docs/FAQ.md)
2. **检查日志**：查看 `claudebot.log` 文件
3. **提交 Issue**：在 [GitHub Issues](https://github.com/zhixuli0406/claudeBot/issues) 提问
4. **社区支持**：在 Telegram/Discord 社区寻求帮助

---

## 迁移检查清单

使用此检查清单确保迁移完整：

- [ ] Claude Code CLI 已安装并可用
- [ ] 备份已创建（.env, cursorbot.db）
- [ ] 环境变量已更新（CURSOR_* → CLAUDE_*）
- [ ] CLAUDE_API_KEY 已设置为有效的 Anthropic API Key
- [ ] 代码已更新到 v2.0.0
- [ ] 依赖已更新（pip install -r requirements.txt）
- [ ] 数据库已自动迁移（或手动复制）
- [ ] 应用可以正常启动
- [ ] 基础命令正常工作（/help, /status, /climodel）
- [ ] AI 对话功能正常
- [ ] 秘书模式功能正常
- [ ] 语音助手正常（如果使用）
- [ ] 原生应用已重新安装并配置（如果使用）
- [ ] Chrome 扩展已更新（如果使用）
- [ ] Docker 部署正常（如果使用）
- [ ] 生产环境部署正常（Railway/Render/Fly.io）

---

## 下一步

迁移完成后，您可以：

1. **探索新功能**：阅读 [CHANGELOG.md](CHANGELOG.md) 了解 v2.0.0 的新特性
2. **优化配置**：根据您的需求调整 Claude Code CLI 设置
3. **更新文档**：如果您有自定义文档，更新相关引用
4. **分享反馈**：在 GitHub 上分享您的迁移体验和建议

---

## 版本信息

- **迁移指南版本**：1.0
- **发布日期**：2026-02-10
- **适用版本**：CursorBot v1.1.0 → ClaudeBot v2.0.0

---

**祝迁移顺利！** 🎉

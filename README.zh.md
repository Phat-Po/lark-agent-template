# Lark Agent Template

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)
[![lark-oapi](https://img.shields.io/badge/lark--oapi-1.4+-0088FF.svg)](https://github.com/larksuite/oapi-sdk-python)

<pre>
██       ████    ███████    ██
██      ██   ██     ██      ██
██      ██████      ██      ██
██      ██   ██     ██      ██
██████  ██   ██     ██      ██
</pre>

**开箱即用的飞书 AI Agent 模板：工具调用、交互式卡片、可观测性框架——5 分钟从克隆到上线。**

📖 [English Documentation](README.md)

---

## 为什么选择 Lark Agent Template？

做一个能真正*做事*的飞书机器人——管理日历、创建任务、搜索文档——通常要写几百行样板代码：API 集成、错误处理、对话记忆、指标监控、幂等性检查。这个模板开箱提供所有这些能力。

| | Lark Agent Template | Feishu-OpenAI | nonebot2-feishu |
|---|:---:|:---:|:---:|
| **语言** | Python 3.11+ | Go | Python |
| **Agent 循环 + 工具调用** | ✅ 内置 | ❌ | ❌ |
| **自动 harness（指标、追踪、幂等性）** | ✅ 每个工具 | ❌ | ❌ |
| **交互式卡片 (CardKit v2)** | ✅ 按钮确认 | ✅ 富文本卡片 | ❌ |
| **LLM 提供商无关** | ✅ 任何 OpenAI 兼容 | ❌ 仅 OpenAI | 通过插件 |
| **数据库持久化确认** | ✅ 重启不丢失 | ❌ | ❌ |
| **可观测性仪表盘** | ✅ 内置 | ❌ | ❌ |
| **克隆即用** | ✅ 5 分钟 | ❌ 配置复杂 | ❌ 框架学习成本 |
| **许可证** | MIT | GPL-3.0 | MIT |

---

## ✨ 功能特性

- 🤖 **Agent 循环** — LLM 决定何时调用工具，结果反馈用于多步推理
- 🎴 **交互式卡片** — 回复以 CardKit v2 卡片渲染（彩色标题 + Markdown）
- ✅ **按钮确认** — 受保护写操作显示确认/取消按钮；SQLite 持久化，重启不丢失
- 🔧 **15 个内置工具** — 日历、任务、文档、云空间、消息、网页搜索
- 📊 **可观测性框架** — 指标、追踪、幂等性、Schema 校验——自动应用于所有工具
- 🧠 **对话记忆** — 会话历史 + 每用户持久化长期记忆
- 🔌 **LLM 提供商无关** — 支持任何 OpenAI 兼容 API（OpenAI、DeepSeek、Mimo、Ollama 等）
- 🛡️ **超时 + 错误处理** — API 调用 15 秒超时，错误消息自动清理，卡片发送失败回退纯文本
- 🐳 **Docker 就绪** — 一条命令构建并运行

---

## 📦 安装

```bash
# 1. 克隆
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env

# 2. 运行（缺少凭证会交互式提示）
docker compose run --rm agent
```

启动时检查凭证，缺失则提示粘贴：

```
============================================================
  Lark Agent Template — Credential Check
============================================================

  LARK_APP_ID is not set.
  Get from: https://open.feishu.cn/app → Credentials & Basic Info

  Enter LARK_APP_ID: cli_xxxxxxxxxxxxxxxx
  Saved to .env
```

凭证设置完成后，机器人自动启动。在飞书中搜索应用名称并发送消息即可测试。

> **想手动配置？** 在 `.env` 中填入 `LARK_APP_ID`、`LARK_APP_SECRET` 和 `LLM_API_KEY`，然后 `docker compose up --build`。

---

## 🚀 快速上手

运行后，在飞书中试试：

| 说 | 效果 |
|-----|------|
| "今天有什么日程？" | 读取日历事件 |
| "创建一个任务：周五前提交报告" | 显示确认卡片，然后创建任务 |
| "搜索文档：Q2 营收" | 搜索飞书文档 |
| "给市场群发消息：下午3点开会" | 显示确认卡片，然后发送 |
| "东京天气怎么样？" | 调用网页搜索工具 |

受保护的写入/删除操作（创建、删除、发送）会显示带 **确认** 和 **取消** 按钮的交互式卡片。待确认操作存储在数据库中——如果机器人重启，操作会在 30 分钟后自动过期。

---

## 🔧 配置说明

所有配置通过环境变量设置。复制 `.env.example` 为 `.env` 并填写：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LARK_APP_ID` | — | 飞书应用 ID（必填） |
| `LARK_APP_SECRET` | — | 飞书应用密钥（必填） |
| `LLM_API_KEY` | — | LLM 提供商 API Key（必填） |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM API 地址 |
| `LLM_MODEL` | `gpt-4o` | 模型名称 |
| `BOT_DISPLAY_NAME` | `Lark Agent` | 卡片标题中显示的机器人名称 |
| `MAX_HISTORY_ROUNDS` | `20` | 上下文中的最大对话轮数 |
| `MAX_HISTORY_TOKENS` | `1800` | 对话历史最大 token 数 |
| `MAX_TOKEN_BUDGET` | `3000` | LLM 响应的最大 token 数 |
| `REQUIRE_WRITE_CONFIRMATION` | `true` | 写入/危险操作前是否需要用户确认 |
| `MESSAGE_DEDUP_SECONDS` | `300` | 消息去重窗口（秒） |
| `SEARCH_API_KEY` | — | SerpAPI Key（可选，用于网页搜索） |
| `DB_PATH` | `data/agent.db` | SQLite 数据库路径 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

切换 LLM 提供商：只需修改 `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL`，无需改代码。

---

## 🛠️ 添加自定义工具

```python
from src.tools.registry import register_tool
from src.harness.result import tool_ok

@register_tool(
    name="get_weather",
    description="Get current weather for a city",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"},
        },
        "required": ["city"],
    },
    risk_level="read",
)
async def get_weather(city: str) -> dict:
    return tool_ok({"city": city, "temp": "25°C"})
```

将文件放入 `src/tools/`，重启即可自动注册，享受完整 harness 覆盖（Schema 校验、指标、追踪、幂等性）。

`risk_level="write"` 或 `"destructive"` 的工具自动获得按钮确认流程，无需额外开发。

---

## 📋 内置工具

| 工具 | 说明 | 风险 |
|------|------|:----:|
| `get_calendar` | 查询日历事件 | read |
| `create_calendar_event` | 创建日程（含参会人） | write |
| `delete_calendar_event` | 删除日程 | destructive |
| `get_tasks` | 查询任务列表（按状态/关键词筛选） | read |
| `get_task` | 按 GUID 查询单个任务 | read |
| `create_task` | 创建任务（含截止日期和负责人） | write |
| `delete_task` | 删除任务 | destructive |
| `search_docs` | 按关键词搜索飞书文档 | read |
| `read_doc` | 读取文档完整内容 | read |
| `create_doc` | 创建新文档 | write |
| `delete_doc` | 删除文档 | destructive |
| `move_file` | 移动文件到目标文件夹 | write |
| `create_folder` | 在云空间创建文件夹 | write |
| `send_message` | 发送消息给用户或群组 | write |
| `search_web` | 通过 SerpAPI 搜索网页 | read |

---

## 🏗️ 架构

```
飞书 ──WebSocket──► Lark Client ──► Agent 循环 ◄──► LLM API
                                        │
                                 工具注册表
                                 (harness 包装)
                                        │
                                  记忆 (SQLite)
                                        │
                                 交互式卡片
                                 (CardKit v2)
```

每个工具调用都经过 harness 层：

```
execute_tool(name, args)
    ├── Schema 校验
    ├── 指标（计数、成功/错误率）
    ├── 追踪（SQLite：工具名、耗时、结果）
    ├── 幂等性检查（写工具）
    ├── 确认守卫（写/破坏性 → 按钮卡片）
    └── 执行工具函数
```

详见 [docs/architecture.md](docs/architecture.md)。

---

## 📖 文档地图

| 文档 | 内容 |
|------|------|
| [docs/onboarding-prompt.md](docs/onboarding-prompt.md) | **粘贴到任何 AI 助手中**，获得一步步的安装引导 |
| [docs/feishu-app-setup.md](docs/feishu-app-setup.md) | 飞书应用创建、权限列表、事件订阅 |
| [docs/architecture.md](docs/architecture.md) | 消息流、Agent 循环、Harness、记忆、卡片 |
| [docs/adding-tools.md](docs/adding-tools.md) | 用 `@register_tool` 构建自定义工具 |
| [docs/deploy-local-docker.md](docs/deploy-local-docker.md) | 用 Docker Compose 在本机运行 |
| [docs/deploy-vps.md](docs/deploy-vps.md) | 部署到 Linux VPS 实现 24/7 运行 |

---

## 🔄 更新

```bash
bash update.sh
```

或手动更新：

```bash
git pull origin main
docker compose up --build
```

---

<details>
<summary>🚀 进阶：VPS 部署</summary>

部署到 Linux VPS 实现 24/7 运行：

```bash
ssh user@your-vps
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env && nano .env
docker compose up -d --build
```

Agent 通过 WebSocket 外连，无需开放入站端口。`restart: unless-stopped` 策略确保崩溃或重启后自动恢复。

详见 [docs/deploy-vps.md](docs/deploy-vps.md)。
</details>

<details>
<summary>🛠️ 开发</summary>

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
pytest
```

开发时热重载：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```
</details>

---

## 📄 许可证

MIT 2026 [Phat-Po](https://github.com/Phat-Po)

---

<div align="center">
  <sub>基于 <a href="https://github.com/larksuite/oapi-sdk-python">lark-oapi</a> 构建 · 如果对你有帮助，点个 Star 吧！</sub>
</div>

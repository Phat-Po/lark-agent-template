# Lark Agent Template

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)

<pre>
██       ████    ███████    ██
██      ██   ██     ██      ██
██      ██████      ██      ██
██      ██   ██     ██      ██
██████  ██   ██     ██      ██
</pre>

**开箱即用的飞书 AI Agent 模板，支持工具调用、可观测性框架和插件扩展。**

[English](README.md)

---

## 5 分钟上手

> **第一次使用？** 把 [这个 Prompt](docs/onboarding-prompt.md) 粘贴到 ChatGPT、Claude、Cursor 或任何 AI 助手中。它会一步步引导你——从创建飞书应用到机器人上线——已完成的步骤会自动跳过。

**三步概览：**

```bash
# 1. 克隆
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env

# 2. 编辑 .env — 填入 LARK_APP_ID、LARK_APP_SECRET 和 LLM_API_KEY
#    （不填会 crash loop — 完整飞书配置清单见 docs/feishu-app-setup.md）

# 3. 运行
docker compose up --build
```

> **第 2 步是必须的。** 没有有效的凭证，机器人无法启动。如果日志中出现 `FeishuChannel requires app_id and app_secret`，说明你跳过了这一步。

日志中出现以下内容，说明机器人已上线：

```
Lark Agent Template started
  Tools: 15 loaded
connected to wss://msg-frontier.feishu.cn/ws/v2 ...
```

在飞书中搜索你的应用名称并发送消息即可测试。

---

## 为什么选择 Lark Agent Template？

做一个能真正*做事*的飞书机器人——管理日历、创建任务、搜索文档——通常要写几百行样板代码：API 集成、错误处理、对话记忆、指标监控、幂等性检查。这个模板开箱提供所有这些能力。

| 功能 | Lark Agent Template | Feishu-OpenAI | nonebot2 |
|------|:-------------------:|:-------------:|:--------:|
| 语言 | Python | Go | Python |
| 工具调用 + 自动 harness | yes | no | no |
| 可观测性（指标、追踪） | 内置 | no | no |
| LLM 提供商无关 | yes | 仅 OpenAI | 通过插件 |
| 模板化（克隆即用） | yes | no | no |
| 对话记忆 | 会话 + 持久化 | yes | 通过插件 |
| Docker 部署 | yes | yes | yes |

---

## 功能特性

- **Agent 循环** — LLM 决定何时调用工具，结果反馈用于多步推理
- **可观测性框架** — 指标、追踪、幂等性、Schema 校验——自动应用于所有工具
- **可扩展** — 用 `@register_tool` 装饰器添加自定义工具，框架自动包装
- **对话记忆** — 会话历史 + 每用户持久化长期记忆
- **LLM 提供商无关** — 支持任何 OpenAI 兼容 API（OpenAI、DeepSeek、Mimo、Ollama 等）
- **15 个内置工具** — 日历、任务、文档、消息、网页搜索
- **写入确认** — 危险操作需要用户确认后才执行

---

## 内置工具

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

## 配置说明

所有配置通过环境变量设置。复制 `.env.example` 为 `.env` 并填写：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LARK_APP_ID` | — | 飞书应用 ID（必填） |
| `LARK_APP_SECRET` | — | 飞书应用密钥（必填） |
| `LLM_API_KEY` | — | LLM 提供商 API Key（必填） |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM API 地址 |
| `LLM_MODEL` | `gpt-4o` | 模型名称 |
| `MAX_HISTORY_ROUNDS` | `20` | 上下文中的最大对话轮数 |
| `MAX_TOKEN_BUDGET` | `3000` | LLM 响应的最大 token 数 |
| `REQUIRE_WRITE_CONFIRMATION` | `true` | 写入/危险操作前是否需要用户确认 |
| `SEARCH_API_KEY` | — | SerpAPI Key（可选，用于网页搜索） |
| `DB_PATH` | `data/agent.db` | SQLite 数据库路径 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

切换 LLM 提供商：只需修改 `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL`，无需改代码。

---

## 添加自定义工具

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

将文件放入 `src/tools/`，重启即可自动注册，享受完整 harness 覆盖。

---

## 文档地图

### 快速上手

| 文档 | 内容 |
|------|------|
| [`docs/onboarding-prompt.md`](docs/onboarding-prompt.md) | **粘贴到任何 AI 助手中**，获得一步步的安装引导。会问你做到哪一步了，自动跳过已完成的步骤。 |
| [`docs/feishu-app-setup.md`](docs/feishu-app-setup.md) | 飞书应用创建、完整权限列表（60+ 个 scope）、事件订阅、发布上线清单。 |

### 工作原理

| 文档 | 内容 |
|------|------|
| [`docs/architecture.md`](docs/architecture.md) | 消息流、Agent 循环、Harness 层、记忆系统、工具注册表。 |
| [`docs/adding-tools.md`](docs/adding-tools.md) | 用 `@register_tool` 构建自定义工具，Harness 自动包装 Schema、指标、追踪。 |

### 部署

| 文档 | 内容 |
|------|------|
| [`docs/deploy-local-docker.md`](docs/deploy-local-docker.md) | 用 Docker Compose 在本机运行。 |
| [`docs/deploy-vps.md`](docs/deploy-vps.md) | 部署到 Linux VPS 实现 24/7 运行。Systemd 服务、防火墙配置。 |

### 快速参考

| 文件 | 说明 |
|------|------|
| [`.env.example`](.env.example) | 所有环境变量及注释说明。复制为 `.env` 使用。 |
| [`AGENTS.md`](AGENTS.md) | 项目治理、技术栈、约束条件。 |
| [`tasks/STATUS.md`](tasks/STATUS.md) | 当前项目状态、已知问题、验证清单。 |

---

## 架构

```
飞书 ──WebSocket──► Lark Client ──► Agent 循环 ◄──► LLM API
                                        │
                                 工具注册表
                                 (harness 包装)
                                        │
                                  记忆 (SQLite)
```

详见 [docs/architecture.md](docs/architecture.md)。

---

<details>
<summary>进阶：VPS 部署</summary>

部署到 Linux VPS 实现 24/7 运行：

```bash
ssh user@your-vps
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env && nano .env
docker compose up -d --build
```

Agent 通过 WebSocket 外连，无需开放入站端口。

详见 [docs/deploy-vps.md](docs/deploy-vps.md)。
</details>

<details>
<summary>开发</summary>

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
pytest
```

运行测试：
```bash
pytest tests/
```
</details>

---

## 许可证

MIT 2026 [Phat-Po](https://github.com/Phat-Po)

---

<div align="center">
  <sub>基于 <a href="https://github.com/larksuite/oapi-sdk-python">lark-oapi</a> 构建 · 如果对你有帮助，点个 Star 吧！</sub>
</div>

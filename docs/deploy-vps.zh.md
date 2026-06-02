# VPS 部署

部署 Agent 到 Linux VPS，实现 24/7 运行。

## 前提条件

- Ubuntu 22.04 VPS（任何云服务商）
- VPS 上已安装 Docker 和 Docker Compose
- 可访问本仓库的 fork
- 已配置飞书应用并启用 WebSocket 模式（参见 [feishu-app-setup.md](feishu-app-setup.md)）

## 步骤

### 1. SSH 登录 VPS 并克隆仓库

```bash
ssh user@your-vps-ip
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
```

### 2. 配置凭证

```bash
cp .env.example .env
nano .env
```

填入 `LARK_APP_ID`、`LARK_APP_SECRET`、`LLM_API_KEY` 和 `LLM_MODEL`。设置 `APP_ENV=production`。

### 3. 后台启动

```bash
docker compose up -d --build
```

### 4. 验证运行

```bash
docker compose logs -f
```

应该看到启动 banner 和 `lark_channel_started` 事件。在飞书中发送测试消息。

### 5. 开机自动重启

`docker-compose.yml` 中的 `restart: unless-stopped` 策略意味着容器在崩溃或 VPS 重启后会自动恢复。

验证：

```bash
docker compose ps
```

### 更新到新版本

```bash
git pull
docker compose up -d --build
```

## 防火墙说明

Agent 通过 WebSocket 外连到飞书服务器和你的 LLM API。不需要入站端口。除了 SSH（端口 22）外，可以安全地保持 VPS 防火墙关闭。

## 非 Docker 部署（可选）

如果不想用 Docker：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

要作为系统服务运行，创建 `/etc/systemd/system/lark-agent.service`：

```
[Unit]
Description=Lark Agent
After=network.target

[Service]
WorkingDirectory=/opt/lark-agent-template
ExecStart=/opt/lark-agent-template/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8080
EnvironmentFile=/opt/lark-agent-template/.env
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```

然后：

```bash
systemctl daemon-reload
systemctl enable lark-agent
systemctl start lark-agent
```

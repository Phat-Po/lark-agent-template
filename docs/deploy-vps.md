# VPS Deployment

Deploy the agent to a Linux VPS for 24/7 availability.

## Prerequisites

- Ubuntu 22.04 VPS (any cloud provider)
- Docker and Docker Compose installed on the VPS
- Git access to your fork of this repo
- A Feishu/Lark app with WebSocket mode enabled (see [feishu-app-setup.md](feishu-app-setup.md))

## Steps

### 1. SSH into your VPS and clone the repo

```
ssh user@your-vps-ip
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
```

### 2. Configure credentials

```
cp .env.example .env
nano .env
```

Fill in `LARK_APP_ID`, `LARK_APP_SECRET`, `LLM_API_KEY`, and `LLM_MODEL`. Set `APP_ENV=production`.

### 3. Start in detached mode

```
docker compose up -d --build
```

### 4. Verify it's running

```
docker compose logs -f
```

You should see the startup banner and `lark_channel_started` event. Send a test message in Feishu.

### 5. Auto-restart on reboot

The `restart: unless-stopped` policy in `docker-compose.yml` means the container restarts automatically if it crashes or if the VPS reboots.

To verify:

```
docker compose ps
```

### Updating to a new version

```
git pull
docker compose up -d --build
```

## Firewall notes

The agent connects outbound to Feishu WebSocket servers and your LLM API. No inbound ports are required. You can safely keep the VPS firewall closed except for SSH (port 22).

## Non-Docker deployment (optional)

If you prefer running without Docker:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

To keep it running as a system service, create `/etc/systemd/system/lark-agent.service`:

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

Then:

```
systemctl daemon-reload
systemctl enable lark-agent
systemctl start lark-agent
```

# Local Docker Deployment

Run the agent on your laptop with a single command.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A Feishu/Lark app with WebSocket mode enabled (see [feishu-app-setup.md](feishu-app-setup.md))
- An LLM API key (OpenAI, DeepSeek, Mimo, or any OpenAI-compatible provider)

## Steps

### 1. Clone the repo

```
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
```

### 2. Configure credentials

```
cp .env.example .env
```

Open `.env` and fill in:
- `LARK_APP_ID` and `LARK_APP_SECRET` from your Feishu app
- `LLM_API_KEY` and `LLM_MODEL` for your LLM provider

### 3. Start the agent

```
docker compose up --build
```

The agent connects via WebSocket — no inbound ports are needed.

### 4. Test it

Send a message to your bot in Feishu. You should see a response within a few seconds.

### 5. View logs

```
docker compose logs -f
```

### 6. Stop the agent

```
docker compose down
```

## Data persistence

SQLite lives in `./data/agent.db` on your host machine. It survives container restarts and rebuilds.

To reset all data:

```
docker compose down
rm -rf data/
docker compose up --build
```

## Hot reload during development

The `docker-compose.yml` mounts `./src` into the container, so Python file changes are visible immediately. Restart the container to pick them up:

```
docker compose restart agent
```

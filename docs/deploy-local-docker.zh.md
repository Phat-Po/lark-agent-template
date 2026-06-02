# 本地 Docker 部署

一条命令在本机运行 Agent。

## 前提条件

- 已安装 Docker 和 Docker Compose
- 已配置飞书应用（参见 [feishu-app-setup.md](feishu-app-setup.md)）

## 步骤

### 1. 克隆并配置

```bash
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env
```

编辑 `.env`，填入 `LARK_APP_ID`、`LARK_APP_SECRET` 和 `LLM_API_KEY`。

### 2. 启动

```bash
docker compose up --build
```

首次启动会下载依赖，约 1-2 分钟。之后启动约 30 秒。

### 3. 验证

日志中应该看到：

```
Lark Agent Template started
  Tools: 15 loaded
connected to wss://msg-frontier.feishu.cn/ws/v2 ...
```

在飞书中搜索应用名称并发送消息测试。

### 4. 后台运行

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

停止：

```bash
docker compose down
```

### 5. 重置数据库

如果需要清空所有对话历史和记忆：

```bash
docker compose down
rm -rf data/
docker compose up --build
```

## 开发时热重载

使用 dev override 挂载 `./src` 到容器中，实现代码修改即时生效：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

不使用 dev override 时，每次修改代码需要重新构建：`docker compose up --build`。

## 常见问题

| 症状 | 原因 | 解决 |
|------|------|------|
| 启动后立即退出 | `.env` 缺少凭证 | 运行 `docker compose run --rm agent`（交互式配置） |
| 端口被占用 | 8080 端口被其他服务使用 | 修改 `docker-compose.yml` 中的端口映射 |
| 构建很慢 | 网络问题 | 使用国内镜像或代理 |

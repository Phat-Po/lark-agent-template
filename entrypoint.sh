#!/bin/bash

# Check required credentials. If missing, prompt user interactively.
# Works with: docker compose run --rm agent  (has stdin)
# Fallback: prints instructions if no tty (docker compose up without -it)

ENV_FILE="/app/.env"

# --- Version check ---
BAKED_COMMIT=$(cat /app/.git-commit 2>/dev/null || echo "unknown")
echo ""
echo "  Version: ${BAKED_COMMIT:0:7}"

# Detect if src/ is volume-mounted (stale code risk)
if mountpoint -q /app/src 2>/dev/null || grep -q "/app/src" /proc/1/mountinfo 2>/dev/null; then
    echo ""
    echo "  WARNING: ./src is mounted as a volume."
    echo "  The container is running YOUR local code, not the built-in code."
    echo "  If you see errors, run:"
    echo "    git pull origin main"
    echo "    docker compose build --no-cache"
    echo "    docker compose run --rm agent"
    echo ""
fi

prompt_var() {
    local var_name="$1"
    local description="$2"
    local current_value="$3"

    if [ -n "$current_value" ]; then
        echo "  $var_name = [SET]"
        return
    fi

    echo ""
    echo "  $var_name is not set."
    echo "  $description"
    echo ""

    # Check if we have a TTY for interactive input
    if [ -t 0 ]; then
        read -rp "  Enter $var_name: " user_input
        if [ -n "$user_input" ]; then
            export "$var_name=$user_input"
            # Append to .env file
            if [ -f "$ENV_FILE" ]; then
                # Remove existing empty entry if present
                sed -i.bak "/^${var_name}=$/d" "$ENV_FILE" 2>/dev/null || true
                # Check if var already exists with value
                if grep -q "^${var_name}=" "$ENV_FILE" 2>/dev/null; then
                    sed -i.bak "s|^${var_name}=.*|${var_name}=${user_input}|" "$ENV_FILE" 2>/dev/null || true
                else
                    echo "${var_name}=${user_input}" >> "$ENV_FILE"
                fi
                rm -f "${ENV_FILE}.bak" 2>/dev/null
            fi
            echo "  Saved to .env"
        else
            echo "  Skipped (empty input)"
        fi
    else
        NO_TTY=1
    fi
}

echo ""
echo "============================================================"
echo "  Lark Agent Template — Credential Check"
echo "============================================================"
echo ""

NO_TTY=0
prompt_var "LARK_APP_ID" "Get from: https://open.feishu.cn/app → Credentials & Basic Info" "$LARK_APP_ID"
prompt_var "LARK_APP_SECRET" "Same page as App ID" "$LARK_APP_SECRET"
prompt_var "LLM_API_KEY" "Your LLM provider (OpenAI/DeepSeek/Mimo)" "$LLM_API_KEY"

echo ""
echo "============================================================"

# Re-check after prompting
missing=""
if [ -z "$LARK_APP_ID" ]; then
    missing="$missing LARK_APP_ID"
fi
if [ -z "$LARK_APP_SECRET" ]; then
    missing="$missing LARK_APP_SECRET"
fi

if [ -n "$missing" ]; then
    echo ""
    echo "  Still missing:$missing"
    echo ""

    if [ "$NO_TTY" = "1" ]; then
        echo "  docker compose up doesn't support interactive input."
        echo "  You have two options:"
        echo ""
        echo "  OPTION A — Edit .env manually:"
        echo "    1. Open .env in a text editor"
        echo "    2. Fill in LARK_APP_ID and LARK_APP_SECRET"
        echo "    3. Run: docker compose up --build"
        echo ""
        echo "  OPTION B — Use interactive mode:"
        echo "    1. Press Ctrl+C to stop this"
        echo "    2. Run: docker compose run --rm agent"
        echo "    3. Paste your credentials when prompted"
        echo ""
    else
        echo "  Edit .env manually and restart: docker compose up --build"
        echo ""
    fi

    echo "  Get credentials: https://open.feishu.cn/app"
    echo "  Full guide: https://github.com/Phat-Po/lark-agent-template"
    echo "              → docs/onboarding-prompt.md"
    echo "============================================================"
    echo ""
    exit 1
fi

echo ""
echo "  All required credentials set. Starting bot..."
echo "============================================================"
echo ""
echo "  NEXT STEPS (after bot starts):"
echo ""
echo "  1. ENABLE PERMISSIONS in Feishu Developer Console:"
echo "     https://open.feishu.cn/app → your app → Permissions & Scopes"
echo ""
echo "     Required (messaging):"
echo "       im:message"
echo "       im:message:send_as_bot"
echo "       im:message:readonly"
echo "       im:message.p2p_msg:readonly"
echo "       im:message.group_at_msg:readonly"
echo ""
echo "     Calendar tools:"
echo "       calendar:calendar"
echo "       calendar:calendar.event:read"
echo "       calendar:calendar.event:create"
echo "       calendar:calendar.event:delete"
echo ""
echo "     Task tools:"
echo "       task:task:read"
echo "       task:task:write"
echo "       task:task"
echo "       task:tasklist:read"
echo ""
echo "     Document & Drive tools:"
echo "       docx:document"
echo "       docx:document:readonly"
echo "       docx:document:create"
echo "       drive:drive"
echo "       drive:drive:readonly"
echo "       drive:drive.search:readonly"
echo ""
echo "     Full list: https://github.com/Phat-Po/lark-agent-template"
echo "                 → docs/feishu-app-setup.md"
echo ""
echo "  2. PUBLISH a new version after adding permissions:"
echo "     Version Management → Create version → Submit → Approve"
echo ""
echo "  3. TEST the bot in Feishu (search your app name and send):"
echo "     \"Hello\"                         → basic reply"
echo "     \"What's on my calendar today?\"  → calendar tool"
echo "     \"Create a task: buy milk\"       → task tool"
echo "     \"Search docs: project\"          → document search"
echo "     \"Search web: AI news 2026\"      → web search (needs SEARCH_API_KEY)"
echo ""
echo "  If a tool fails with 'permission denied', you're missing a scope."
echo "  Add it in Permissions & Scopes, publish a new version, try again."
echo ""
echo "============================================================"
echo ""

exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8080

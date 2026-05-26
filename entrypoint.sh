#!/bin/bash

# Check required credentials. If missing, prompt user interactively.
# Works with: docker compose run --rm agent  (has stdin)
# Fallback: prints instructions if no tty (docker compose up without -it)

ENV_FILE="/app/.env"

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
        echo "  No interactive terminal. Set this in .env and restart."
    fi
}

echo ""
echo "============================================================"
echo "  Lark Agent Template — Credential Check"
echo "============================================================"
echo ""

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
    echo "  Edit .env manually and restart: docker compose up --build"
    echo ""
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

exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8080

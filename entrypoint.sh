#!/bin/bash
set -e

# Check required credentials before starting uvicorn.
# If missing, print clear instructions and exit (no crash loop).

missing=""

if [ -z "$LARK_APP_ID" ]; then
    missing="$missing\n  LARK_APP_ID      (get from https://open.feishu.cn/app → Credentials)"
fi

if [ -z "$LARK_APP_SECRET" ]; then
    missing="$missing\n  LARK_APP_SECRET  (same page as App ID)"
fi

if [ -n "$missing" ]; then
    echo ""
    echo "============================================================"
    echo "  MISSING CREDENTIALS — cannot start bot"
    echo ""
    echo -e "  Required but not set:$missing"
    echo ""
    echo "  Fix: edit .env and fill in the values above."
    echo "  Then restart: docker compose up --build"
    echo ""
    echo "  Full guide: https://github.com/Phat-Po/lark-agent-template"
    echo "              → docs/onboarding-prompt.md"
    echo "============================================================"
    echo ""
    exit 1
fi

exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8080

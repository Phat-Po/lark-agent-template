#!/bin/bash
set -e

echo ""
echo "============================================================"
echo "  Lark Agent Template — Update"
echo "============================================================"
echo ""

# Pull latest code
echo "  Pulling latest code..."
git pull origin main
echo ""

# Get commit hash for build arg
GIT_COMMIT=$(git rev-parse HEAD)
echo "  Building image (commit: ${GIT_COMMIT:0:7})..."
echo ""

# Rebuild with no cache
GIT_COMMIT="$GIT_COMMIT" docker compose build --no-cache

echo ""
echo "============================================================"
echo "  Update complete. Starting bot..."
echo "============================================================"
echo ""

# Start the bot
docker compose run --rm agent

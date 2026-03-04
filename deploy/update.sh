#!/bin/bash
# =============================================================================
# SATYA — Pull latest code and restart
# Run this whenever you push new changes from your local machine.
#
# Workflow:
#   Local: git add . && git commit -m "fix" && git push
#   EC2:   ./deploy/update.sh
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "======================================="
echo "  SATYA — Updating"
echo "======================================="

cd "$PROJECT_DIR"

# ── Pull latest code ───────────────────────────────────────────────────────
echo "[1/4] Pulling latest code..."
git pull origin master

# ── Reinstall Python deps if requirements.txt changed ─────────────────────
if git diff HEAD@{1} HEAD --name-only 2>/dev/null | grep -q "requirements.txt"; then
    echo "[2/4] requirements.txt changed — reinstalling Python packages..."
    source .venv/bin/activate
    pip install -r backend/requirements.txt --quiet
else
    echo "[2/4] requirements.txt unchanged — skipping pip install."
fi

# ── Rebuild frontend if frontend/ changed ─────────────────────────────────
if git diff HEAD@{1} HEAD --name-only 2>/dev/null | grep -q "^frontend/"; then
    echo "[3/4] Frontend changes detected — rebuilding..."
    cd frontend
    npm install --silent
    npm run build
    cd "$PROJECT_DIR"
else
    echo "[3/4] No frontend changes — skipping rebuild."
fi

# ── Restart all processes ─────────────────────────────────────────────────
echo "[4/4] Restarting all processes..."
bash "$SCRIPT_DIR/start.sh"

echo "Update complete."

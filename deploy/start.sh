#!/bin/bash
# =============================================================================
# SATYA — Start all processes
# Launches API + 4 workers inside named screen sessions.
# Safe to run multiple times — kills existing sessions first.
#
# Usage:
#   ./deploy/start.sh
#
# Monitor logs:
#   tail -f /tmp/satya-api.log
#   screen -r satya-api       (Ctrl+A, D to detach)
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
BACKEND="$PROJECT_DIR/backend"

# Verify .env exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "ERROR: .env not found at $PROJECT_DIR/.env"
    echo "Copy it from local: scp -i satya-key.pem .env ubuntu@<IP>:$PROJECT_DIR/.env"
    exit 1
fi

# Verify venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: .venv not found. Run setup.sh first."
    exit 1
fi

echo "======================================="
echo "  SATYA — Starting all processes"
echo "======================================="

# ── Kill existing sessions ─────────────────────────────────────────────────
for SESSION in satya-api satya-video satya-audio satya-text satya-scoring; do
    screen -S "$SESSION" -X quit 2>/dev/null || true
done
sleep 1

# ── Start FastAPI (port 8000) ─────────────────────────────────────────────
screen -dmS satya-api bash -c "
    cd $BACKEND
    $VENV_PYTHON -m uvicorn api.main:app \
        --host 0.0.0.0 --port 8000 \
        --workers 2 \
        2>&1 | tee /tmp/satya-api.log
"

echo "  [1/5] satya-api      started (port 8000)"
sleep 2   # Give API time to bind before workers start polling

# ── Start workers ─────────────────────────────────────────────────────────
screen -dmS satya-video bash -c "
    cd $BACKEND
    $VENV_PYTHON -m workers.video_worker.worker 2>&1 | tee /tmp/satya-video.log
"
echo "  [2/5] satya-video    started"

screen -dmS satya-audio bash -c "
    cd $BACKEND
    $VENV_PYTHON -m workers.audio_worker.worker 2>&1 | tee /tmp/satya-audio.log
"
echo "  [3/5] satya-audio    started"

screen -dmS satya-text bash -c "
    cd $BACKEND
    $VENV_PYTHON -m workers.text_worker.worker 2>&1 | tee /tmp/satya-text.log
"
echo "  [4/5] satya-text     started"

screen -dmS satya-scoring bash -c "
    cd $BACKEND
    $VENV_PYTHON -m workers.scoring_worker.worker 2>&1 | tee /tmp/satya-scoring.log
"
echo "  [5/5] satya-scoring  started"

echo ""
echo "All processes running."
echo ""
echo "Commands:"
echo "  screen -ls                    List all sessions"
echo "  screen -r satya-api           Attach to API logs (Ctrl+A D to detach)"
echo "  tail -f /tmp/satya-api.log    Stream API logs without attaching"
echo "  tail -f /tmp/satya-video.log  Stream video worker logs"
echo ""
echo "Health check:"
echo "  curl http://localhost:8000/health"
echo ""

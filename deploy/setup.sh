#!/bin/bash
# =============================================================================
# SATYA — One-time EC2 setup script
# Run once after launching a fresh Ubuntu 22.04 t3.medium instance.
#
# Usage:
#   chmod +x setup.sh && ./setup.sh
# =============================================================================
set -e

PROJECT_DIR="/home/ubuntu/satya"
REPO_URL="https://github.com/Imperiex-1911/SATYA.git"

echo "======================================="
echo "  SATYA — EC2 Setup"
echo "======================================="

# ── 1. System packages ─────────────────────────────────────────────────────
echo "[1/7] Installing system packages..."
sudo apt-get update -y
sudo apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    nginx \
    git screen \
    ffmpeg \
    libsndfile1 \
    curl

# Node.js 20 LTS via NodeSource (Ubuntu default apt gives v12 which is too old for Vite 5)
echo "  Installing Node.js 20 LTS..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# ── 2. Clone repository ────────────────────────────────────────────────────
echo "[2/7] Cloning repository..."
if [ -d "$PROJECT_DIR" ]; then
    echo "  Directory already exists — pulling latest..."
    cd "$PROJECT_DIR" && git pull origin master
else
    git clone "$REPO_URL" "$PROJECT_DIR"
fi
cd "$PROJECT_DIR"

# ── 3. Python virtual environment ──────────────────────────────────────────
echo "[3/7] Setting up Python virtual environment..."
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r backend/requirements.txt --quiet
echo "  Python packages installed."

# ── 4. Build React frontend ────────────────────────────────────────────────
echo "[4/7] Building React frontend..."
cd "$PROJECT_DIR/frontend"
npm install --silent
npm run build
cd "$PROJECT_DIR"
echo "  Frontend built → frontend/dist/"

# ── 5. Configure nginx ─────────────────────────────────────────────────────
echo "[5/7] Configuring nginx..."
sudo cp "$PROJECT_DIR/deploy/nginx.conf" /etc/nginx/sites-available/satya
sudo ln -sf /etc/nginx/sites-available/satya /etc/nginx/sites-enabled/satya
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
echo "  nginx configured."

# ── 6. .env reminder ──────────────────────────────────────────────────────
echo "[6/7] Checking .env..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo ""
    echo "  ⚠  .env NOT FOUND — you must create it before starting SATYA."
    echo ""
    echo "  Copy from your local machine:"
    echo "    scp -i satya-key.pem .env ubuntu@<EC2_IP>:/home/ubuntu/satya/.env"
    echo ""
else
    echo "  .env found."
fi

# ── 7. Whisper model pre-download ────────────────────────────────────────
echo "[7/7] Pre-downloading Whisper 'small' model (~244MB)..."
source "$PROJECT_DIR/.venv/bin/activate"
python3 -c "
from faster_whisper import WhisperModel
print('  Downloading model...')
WhisperModel('small', device='cpu', compute_type='int8')
print('  Whisper model ready.')
" || echo "  Whisper pre-download skipped (will download on first use)."

echo ""
echo "======================================="
echo "  Setup complete!"
echo "======================================="
echo ""
echo "Next steps:"
echo "  1. If .env is missing: scp -i satya-key.pem .env ubuntu@<IP>:/home/ubuntu/satya/.env"
echo "  2. Start everything:   /home/ubuntu/satya/deploy/start.sh"
echo "  3. Check status:       screen -ls"
echo "  4. API health check:   curl http://localhost:8000/health"
echo "  5. Open in browser:    http://<EC2_ELASTIC_IP>"
echo ""

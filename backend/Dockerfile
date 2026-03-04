FROM python:3.10-slim

WORKDIR /app

# System dependencies for FFmpeg and audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies — split into two layers so Docker caches the fast
# API packages and only re-downloads heavy worker packages on retry
COPY requirements.txt .

# Light API packages (fast — installs in < 30s)
RUN pip install --no-cache-dir --timeout=120 \
    fastapi==0.115.0 \
    "uvicorn[standard]==0.32.0" \
    boto3==1.35.0 \
    pydantic==2.9.0 \
    pydantic-settings==2.6.0 \
    python-dotenv==1.0.1 \
    httpx==0.28.0 \
    python-multipart==0.0.12 \
    "yt-dlp>=2024.12.0" \
    langdetect==1.0.9

# Heavy ML packages (slow — give each package 5 minutes)
RUN pip install --no-cache-dir --timeout=300 numpy==1.26.4 Pillow==11.1.0
RUN pip install --no-cache-dir --timeout=300 scipy==1.14.0
RUN pip install --no-cache-dir --timeout=300 scikit-image==0.24.0
RUN pip install --no-cache-dir --timeout=300 opencv-python-headless==4.10.0.84
RUN pip install --no-cache-dir --timeout=300 mediapipe==0.10.14

# Application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including TensorFlow Lite requirements
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    portaudio19-dev \
    libsndfile1 \
    wget \
    ffmpeg \
    libhdf5-dev \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
# Note: birdnetlib will download model files on first run (~100MB)
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download BirdNET model (optional but recommended)
RUN python -c "from birdnetlib import Recording; Recording(None, lat=0, lon=0, min_conf=0.5)" || true

# Copy application code
COPY src/ ./src/

# Create data directory
RUN mkdir -p /app/data

# Expose API port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LISTENER_DB_PATH=/app/data/detections.db

# Run the application
CMD ["python", "src/main.py"]
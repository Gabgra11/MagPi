FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    portaudio19-dev \
    libsndfile1 \
    ffmpeg \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Trigger BirdNET-Lite model download at image build time.
RUN python - <<'PY'
import pathlib, sys
try:
    import birdnetlib
    base = pathlib.Path(birdnetlib.__file__).parent
    model_dir = base / 'models' / 'lite'
    model_dir.mkdir(parents=True, exist_ok=True)
    from birdnetlib.analyzer_lite import LiteAnalyzer
    LiteAnalyzer()
except Exception as e:
    print('ERROR during LiteAnalyzer initialization:', e, file=sys.stderr)
    raise
PY

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
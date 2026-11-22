FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-tam ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false FASTEMBED_CACHE=/app/.fastembed

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the embedding model while building, so the server does not download it at start-up
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='/app/.fastembed')"

COPY . /app

# Render gives the port in $PORT. One worker only, to save memory.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]

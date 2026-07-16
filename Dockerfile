FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install --no-cache-dir --user -r requirements.txt


FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY configs/ configs/
COPY src/ src/

# Pre-download models so container startup does not block on first request.
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2'); print('Models pre-downloaded successfully.')"

EXPOSE 8000

# Qdrant local uses a file lock, so this container must run as a single worker.
CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends     gcc g++     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user --index-url https://download.pytorch.org/whl/cpu torch     && pip install --no-cache-dir --user -r requirements.txt


FROM python:3.12-slim AS runtime

# The embedding revision is pinned at build time so the model downloaded in
# the image is exactly the revision the index manifest and runtime expect.
ARG EMBEDDING_MODEL_ID=nomic-ai/nomic-embed-text-v1.5
ARG EMBEDDING_MODEL_REVISION=e9b6763023c676ca8431644204f50c2b100d9aab
ARG RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
ARG GIT_REVISION=unknown

LABEL org.opencontainers.image.title="Enterprise Document QA"
LABEL org.opencontainers.image.description="RAG over SEC 10-K filings: hybrid retrieval, grounded generation, cited streaming answers"
LABEL org.opencontainers.image.revision=${GIT_REVISION}
LABEL org.opencontainers.image.source="https://github.com/NamTV2712/Enterprise-Document-QA-"
LABEL ai.edqa.embedding-model=${EMBEDDING_MODEL_ID}
LABEL ai.edqa.embedding-revision=${EMBEDDING_MODEL_REVISION}
LABEL ai.edqa.reranker-model=${RERANKER_MODEL}

WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY configs/ configs/
COPY src/ src/

# Pre-download the exact pinned models so container startup does not block on
# first request and so runtime loading can be verified with HF offline flags.
RUN python -c "import os; from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('$EMBEDDING_MODEL_ID', revision='$EMBEDDING_MODEL_REVISION', trust_remote_code=True); CrossEncoder('$RERANKER_MODEL'); print('Pinned models pre-downloaded successfully.')"

ENV EMBEDDING_MODEL_ID=${EMBEDDING_MODEL_ID}
ENV EMBEDDING_MODEL_REVISION=${EMBEDDING_MODEL_REVISION}
ENV GIT_REVISION=${GIT_REVISION}

EXPOSE 8000

# Qdrant local uses a file lock, so this container must run as a single worker.
# Uvicorn forwarded-header handling is disabled: the application owns
# X-Forwarded-For interpretation through TRUSTED_PROXY_CIDRS, and two layers
# rewriting the client would corrupt rate-limit identity.
CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]

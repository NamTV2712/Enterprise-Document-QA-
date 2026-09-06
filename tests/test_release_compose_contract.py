"""Serving-configuration contract between docker-compose.yml and Settings.

The documented environment variables must actually reach the container.
This test parses docker-compose.yml as text (no Docker required) and
verifies with fake values that every serving-critical variable is forwarded,
that evaluation-only configuration is NOT forwarded, and that security
defaults stay off.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"
DOCKERFILE_PATH = REPO_ROOT / "Dockerfile"


def _compose_text() -> str:
    return COMPOSE_PATH.read_text(encoding="utf-8")


def _environment_block(text: str) -> str:
    match = re.search(r"environment:\n((?:[ \t]+[^\n]*\n)+)", text)
    assert match, "docker-compose.yml has no environment block"
    return match.group(1)


def _env_names(block: str) -> list[str]:
    names = []
    for line in block.splitlines():
        match = re.match(r"\s*- ([A-Z_0-9]+)=", line)
        if match:
            names.append(match.group(1))
    return names


def test_serving_critical_variables_are_forwarded() -> None:
    names = _env_names(_environment_block(_compose_text()))
    required = [
        "GROQ_API_KEY",
        "GROQ_API_KEY2",
        "GROQ_API_KEY3",
        "GROQ_API_KEY4",
        "GROQ_API_KEY5",
        "QDRANT_MODE",
        "QDRANT_LOCAL_PATH",
        "QDRANT_INDEX_MANIFEST_PATH",
        "EMBEDDING_MODEL_ID",
        "EMBEDDING_MODEL_REVISION",
        "RERANKER_MODEL_ID",
        "RERANKER_MODEL_REVISION",
        "ALLOWED_ORIGINS",
        "TRUSTED_PROXY_CIDRS",
        "LLM_RATE_LIMIT_BURST",
        "LLM_RATE_LIMIT_DAILY",
        "DECOMPOSED_RATE_LIMIT",
        "CACHE_TEST_RATE_LIMIT",
        "ENABLE_CACHE_CLEAR",
        "ENABLE_METRICS_ENDPOINT",
        "GIT_REVISION",
    ]
    missing = [name for name in required if name not in names]
    assert not missing, f"Documented serving variables never reach the container: {missing}"


def test_evaluation_generation_keys_are_not_forwarded() -> None:
    """The evaluation-generation pool keys must stay out of the serving image."""
    names = _env_names(_environment_block(_compose_text()))
    assert "GROQ_API_KEY_FALL_BACK" not in names
    assert "GROQ_API_KEY_FALL_BACK2" not in names
    assert "EMBEDDING_GENERATION_PATH" not in names
    assert "EMBEDDING_GENERATIONS_DIR" not in names


def test_security_defaults_stay_off() -> None:
    block = _environment_block(_compose_text())
    assert re.search(r"- ENABLE_CACHE_CLEAR=false\b", block)
    assert re.search(r"- ENABLE_METRICS_ENDPOINT=false\b", block)


def test_dockerfile_pins_model_revisions_and_disables_proxy_headers() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    assert "ARG EMBEDDING_MODEL_REVISION" in dockerfile
    assert "e9b6763023c676ca8431644204f50c2b100d9aab" in dockerfile
    assert "SentenceTransformer('$EMBEDDING_MODEL_ID', revision='$EMBEDDING_MODEL_REVISION'" in dockerfile
    assert "ARG RERANKER_MODEL_REVISION" in dockerfile
    assert "CrossEncoder('$RERANKER_MODEL', revision='$RERANKER_MODEL_REVISION')" in dockerfile
    assert "--no-proxy-headers" in dockerfile
    assert '"--workers", "1"' in dockerfile


def test_dockerfile_labels_carry_revision() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    assert "org.opencontainers.image.revision=${GIT_REVISION}" in dockerfile
    assert "ai.edqa.embedding-revision=${EMBEDDING_MODEL_REVISION}" in dockerfile
    assert "ai.edqa.reranker-revision=${RERANKER_MODEL_REVISION}" in dockerfile


def test_compose_image_tag_follows_git_revision() -> None:
    compose = _compose_text()
    assert re.search(r"image: edqa-api:\$\{GIT_REVISION", compose)

"""
Module: semantic_cache.py
Filter-aware semantic cache for RAG responses.

The cache key is the query embedding plus exact request filters
(`ticker`, `section`, `top_k`). This avoids reusing an answer across
different corpus slices.
"""

import logging
import threading
import time
from dataclasses import asdict, dataclass

import numpy as np

logger = logging.getLogger(__name__)


def make_filter_key(ticker: str | None, section: str | None, top_k: int) -> str:
    """Create a stable string key from request filters."""
    return f"{ticker or '*'}|{section or '*'}|{top_k}"


@dataclass
class CacheEntry:
    query_embedding: list[float]
    filter_key: str
    answer: str
    sources: list[dict]
    model_used: str
    timestamp: float
    hit_count: int = 0


@dataclass
class CacheStats:
    total_requests: int = 0
    cache_hits: int = 0
    entries: int = 0
    max_entries: int = 0
    similarity_threshold: float = 0.0
    ttl_seconds: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.cache_hits / self.total_requests, 4)


class SemanticCache:
    """In-memory semantic cache using cosine similarity.

    The MVP implementation uses a list scan to keep dependencies simple.
    At production scale, this interface can be backed by a dedicated Qdrant
    collection with an ANN index and a payload filter on `filter_key`.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        max_entries: int = 500,
        ttl_seconds: int = 3600,
    ):
        self.threshold = similarity_threshold
        self.max_entries = max_entries
        self.ttl = ttl_seconds
        self._entries: list[CacheEntry] = []
        self._lock = threading.RLock()
        self._stats = CacheStats(
            max_entries=max_entries,
            similarity_threshold=similarity_threshold,
            ttl_seconds=ttl_seconds,
        )

    def get(
        self,
        query_embedding: list[float],
        ticker: str | None,
        section: str | None,
        top_k: int,
    ) -> CacheEntry | None:
        """Return the best matching cache entry, or None on miss."""
        with self._lock:
            self._stats.total_requests += 1
            now = time.monotonic()
            filter_key = make_filter_key(ticker, section, top_k)

            candidates = [
                entry
                for entry in self._entries
                if entry.filter_key == filter_key and (now - entry.timestamp) <= self.ttl
            ]
            if not candidates:
                return None

            q_norm = self._normalize(query_embedding)
            best_score = -1.0
            best_entry = None
            for entry in candidates:
                score = float(np.dot(q_norm, self._normalize(entry.query_embedding)))
                if score > best_score:
                    best_score = score
                    best_entry = entry

            if best_entry is not None and best_score >= self.threshold:
                best_entry.hit_count += 1
                self._stats.cache_hits += 1
                logger.info("Cache HIT (similarity=%.4f, filter=%s)", best_score, filter_key)
                return best_entry

        logger.debug(
            "Cache MISS (best_similarity=%.4f, threshold=%.2f, filter=%s)",
            best_score,
            self.threshold,
            filter_key,
        )
        return None

    def set(
        self,
        query_embedding: list[float],
        ticker: str | None,
        section: str | None,
        top_k: int,
        answer: str,
        sources: list[dict],
        model_used: str,
    ) -> None:
        """Store a response and evict expired or least-used entries if needed."""
        with self._lock:
            now = time.monotonic()
            self._prune_expired(now)

            if len(self._entries) >= self.max_entries:
                self._entries.sort(key=lambda entry: (entry.hit_count, entry.timestamp))
                evicted = self._entries.pop(0)
                logger.debug("Cache evicted: filter=%s", evicted.filter_key)

            self._entries.append(
                CacheEntry(
                    query_embedding=query_embedding,
                    filter_key=make_filter_key(ticker, section, top_k),
                    answer=answer,
                    sources=sources,
                    model_used=model_used,
                    timestamp=now,
                )
            )
            self._stats.entries = len(self._entries)

    def test_similarity(self, embedding_a: list[float], embedding_b: list[float]) -> float:
        """Return cosine similarity for threshold tuning."""
        return float(np.dot(self._normalize(embedding_a), self._normalize(embedding_b)))

    def get_stats(self) -> dict:
        with self._lock:
            self._prune_expired(time.monotonic())
            self._stats.entries = len(self._entries)
            return {**asdict(self._stats), "hit_rate": self._stats.hit_rate}

    def clear(self) -> int:
        """Clear all cache entries and reset metrics."""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._stats = CacheStats(
                max_entries=self.max_entries,
                similarity_threshold=self.threshold,
                ttl_seconds=self.ttl,
            )
            return count

    def _prune_expired(self, now: float) -> None:
        self._entries = [entry for entry in self._entries if (now - entry.timestamp) <= self.ttl]

    @staticmethod
    def _normalize(vector: list[float]) -> np.ndarray:
        arr = np.array(vector, dtype=np.float32)
        return arr / (np.linalg.norm(arr) + 1e-10)

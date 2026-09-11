from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM API keys
    groq_api_key: str = ""
    groq_api_key2: str = ""
    groq_api_key3: str = ""
    groq_api_key4: str = ""
    groq_api_key5: str = ""
    groq_api_key_fall_back: str = ""
    groq_api_key_fall_back2: str = ""
    # ``pool`` preserves legacy rotation; improvement/evaluation runs set
    # ``key5_only`` so every provider call is auditable against GROQ_API_KEY5.
    groq_key_policy: str = "pool"

    # Data path (relative path to run on any machine)
    data_raw_dir: Path = Path("data/raw")
    data_processed_dir: Path = Path("data/processed")
    data_public_evaluations_dir: Path = Path("data/public_evaluations")

    # Optional contact identity for bounded on-demand SEC reader acquisition.
    # Acquisition fails closed when this is empty or lacks a contact address.
    sec_reader_user_agent: str = ""

    # Bounded, local-only normalized original viewer. These values are
    # deliberately conservative; the viewer validates them against hard
    # ceilings before serving any source content.
    viewer_raw_file_max_bytes: int = 20 * 1024 * 1024
    viewer_raw_file_hard_max_bytes: int = 32 * 1024 * 1024
    viewer_processed_file_max_bytes: int = 20 * 1024 * 1024
    viewer_processed_file_hard_max_bytes: int = 32 * 1024 * 1024
    viewer_companion_max: int = 4
    viewer_companion_hard_max: int = 8
    viewer_source_set_max_bytes: int = 40 * 1024 * 1024
    viewer_source_set_hard_max_bytes: int = 64 * 1024 * 1024
    viewer_normalized_source_max_codepoints: int = 4_000_000
    viewer_normalized_source_hard_max_codepoints: int = 8_000_000
    viewer_normalized_set_max_codepoints: int = 8_000_000
    viewer_normalized_set_hard_max_codepoints: int = 16_000_000
    viewer_window_default: int = 16_000
    viewer_window_max: int = 32_000
    viewer_find_default_limit: int = 20
    viewer_find_max_limit: int = 100
    viewer_max_pending_jobs: int = 8
    viewer_cache_entries: int = 4
    viewer_cache_max_bytes: int = 32 * 1024 * 1024

    # Qdrant configuration. Keep local as the safe default until cloud migration is verified.
    qdrant_mode: str = "local"
    qdrant_local_path: Path = Path("data/processed/qdrant")
    qdrant_index_manifest_path: Path = Path(
        "data/processed/qdrant_index_manifest.json"
    )
    qdrant_cloud_url: str = ""
    qdrant_cloud_api_key: str = ""

    # Required provenance for trusted embedding/index rebuilds.
    embedding_model_id: str = "nomic-ai/nomic-embed-text-v1.5"
    embedding_model_revision: str = ""
    reranker_model_id: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_model_revision: str = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
    embedding_generations_dir: Path = Path("data/embedding_generations")
    embedding_generation_path: Path | None = None

    # Browser origins allowed to call the API. Add the deployed frontend URL via env.
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    # Public API protection. In-memory limits are appropriate for the single-worker runtime.
    llm_rate_limit_burst: str = "10/minute"
    llm_rate_limit_daily: str = "100/day"
    decomposed_rate_limit: str = "5/minute"
    cache_test_rate_limit: str = "10/minute"
    enable_cache_clear: bool = False
    enable_metrics_endpoint: bool = False

    # Comma-separated CIDR ranges of reverse proxies trusted to set
    # X-Forwarded-For (for example an ngrok tunnel or Docker gateway).
    # Empty by default: rate limits then key on the socket peer address,
    # and forwarded headers from anyone are ignored.
    trusted_proxy_cidrs: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


settings = Settings()

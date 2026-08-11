from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM API keys
    groq_api_key: str = ""
    groq_api_key_fall_back: str = ""

    # Data path (relative path to run on any machine)
    data_raw_dir: Path = Path("data/raw")
    data_processed_dir: Path = Path("data/processed")

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

    @property
    def allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


settings = Settings()

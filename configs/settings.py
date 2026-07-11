from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM API keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # Data path (relative path to run on any machine)
    data_raw_dir: Path = Path("data/raw")
    data_processed_dir: Path = Path("data/processed")

    # Qdrant configuration. Keep local as the safe default until cloud migration is verified.
    qdrant_mode: str = "local"
    qdrant_local_path: Path = Path("data/processed/qdrant")
    qdrant_cloud_url: str = ""
    qdrant_cloud_api_key: str = ""

settings = Settings()

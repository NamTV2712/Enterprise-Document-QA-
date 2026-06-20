from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM API keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Data path (relative path to run on any machine)
    data_raw_dir: Path = Path("data/raw")
    data_processed_dir: Path = Path("data/processed")

settings = Settings()
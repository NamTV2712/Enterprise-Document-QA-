from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 500
    chunk_overlap: int = 50

    class Config:
        env_file = ".env"


settings = Settings()

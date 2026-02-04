from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://healthcare:healthcare123@postgres:5432/healthcare"

    # Ollama
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"

    # ChromaDB
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000

    # Hidden Layer
    hiddenlayer_client_id: str = ""
    hiddenlayer_client_secret: str = ""
    hiddenlayer_api_url: str = "https://api.hiddenlayer.ai"

    # AIM Security
    aim_api_key: str = ""
    aim_api_url: str = "https://api.aim.security"

    # App
    upload_dir: str = "/app/uploads"
    secret_key: str = "change-this-to-a-random-string"

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # ChromaDB
    chromadb_host: str = Field(default="chromadb", env="CHROMADB_HOST")
    chromadb_port: int = Field(default=8000, env="CHROMADB_PORT")
    
    # Ollama
    ollama_base_url: str = Field(default="http://ollama:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:3b", env="OLLAMA_MODEL")
    ollama_embed_model: str = Field(default="nomic-embed-text", env="OLLAMA_EMBED_MODEL")
    
    # LiteLLM
    litellm_base_url: str = Field(default="http://litellm:4000", env="LITELLM_BASE_URL")
    litellm_master_key: str = Field(default="sk-1234", env="LITELLM_MASTER_KEY")
    litellm_virtual_key: str = Field(default="", env="LITELLM_VIRTUAL_KEY")
    
    # Hidden Layer
    hiddenlayer_client_id: str = Field(..., env="HIDDENLAYER_CLIENT_ID")
    hiddenlayer_client_secret: str = Field(..., env="HIDDENLAYER_CLIENT_SECRET")
    hiddenlayer_api_url: str = Field(
        default="https://api.hiddenlayer.ai",
        env="HIDDENLAYER_API_URL"
    )
    
    # AIM
    aim_api_key: str = Field(..., env="AIM_API_KEY")
    aim_api_url: str = Field(
        default="https://api.aim.security",
        env="AIM_API_URL"
    )
    
    # File uploads
    upload_dir: str = Field(default="/app/uploads", env="UPLOAD_DIR")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

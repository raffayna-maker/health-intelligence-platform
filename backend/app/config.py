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
    
    # AWS Bedrock
    aws_access_key_id: str = Field(default="", env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    aws_bedrock_model_id: str = Field(
        default="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        env="AWS_BEDROCK_MODEL_ID",
    )
    aws_bedrock_embed_model_id: str = Field(
        default="amazon.titan-embed-text-v2:0",
        env="AWS_BEDROCK_EMBED_MODEL_ID",
    )
    
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
    hiddenlayer_project_id: str = Field(default="", env="HIDDENLAYER_PROJECT_ID")
    
    # AIM
    aim_api_key: str = Field(..., env="AIM_API_KEY")
    aim_api_url: str = Field(
        default="https://api.aim.security",
        env="AIM_API_URL"
    )

    # PromptFoo Guardrails
    promptfoo_api_key: str = Field(default="", env="PROMPTFOO_API_KEY")
    promptfoo_target_id: str = Field(default="", env="PROMPTFOO_TARGET_ID")
    promptfoo_api_url: str = Field(
        default="https://www.promptfoo.app",
        env="PROMPTFOO_API_URL"
    )

    # MCP Servers
    mcp_legitimate_url: str = Field(default="http://mcp-server:5010", env="MCP_LEGITIMATE_URL")
    mcp_attacker_url: str = Field(default="http://mcp-attacker:5011", env="MCP_ATTACKER_URL")
    # Legacy alias — still works if set in .env, but runtime toggle is preferred for demos
    mcp_server_url: str = Field(default="http://mcp-server:5010", env="MCP_SERVER_URL")

    # File uploads
    upload_dir: str = Field(default="/app/uploads", env="UPLOAD_DIR")

    # Gmail SMTP
    gmail_address: str = Field(default="", env="GMAIL_ADDRESS")
    gmail_app_password: str = Field(default="", env="GMAIL_APP_PASSWORD")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

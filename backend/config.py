"""
Configuration management for Commander backend.

Uses Pydantic Settings for type-safe configuration with .env file support.
"""
from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""
    
    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Paths
    data_dir: Path = Field(default=_BACKEND_DIR / "data")
    gmail_credentials_file: Path | None = None
    
    # LLM Settings
    openai_api_key: str = Field(default="")
    llm_model: str = Field(default="gpt-4o-mini")
    
    # Embedding Settings
    embedding_model: str = Field(default="text-embedding-3-small")
    max_embedding_tokens: int = Field(default=8000)
    
    # Qdrant Settings
    qdrant_url: str = Field(default="")
    qdrant_api_key: str = Field(default="")
    qdrant_collection_name: str = Field(default="commander_contexts")
    
    # API Settings
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    debug: bool = Field(default=False)
    
    @property
    def gmail_credentials_path(self) -> Path:
        """Get Gmail credentials file path, defaulting to data_dir if not set."""
        if self.gmail_credentials_file:
            return self.gmail_credentials_file
        return self.data_dir / "gmail_credentials.json"
    
    def validate_config(self) -> list[str]:
        """Validate configuration and return list of warnings/errors."""
        issues = []
        
        if not self.openai_api_key:
            issues.append("OPENAI_API_KEY is not set")
        
        if not self.qdrant_url:
            issues.append("QDRANT_URL is not set")
        
        if not self.qdrant_api_key:
            issues.append("QDRANT_API_KEY is not set")
        
        if not self.gmail_credentials_path.exists():
            issues.append(f"Gmail credentials file not found: {self.gmail_credentials_path}")
        
        if not self.data_dir.exists():
            issues.append(f"Data directory does not exist: {self.data_dir}")
        
        return issues


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    issues = settings.validate_config()
    
    if issues:
        print(f"Issues: {issues}")
        raise ValueError(f"Invalid configuration: {issues}")

    return settings


settings = get_settings()

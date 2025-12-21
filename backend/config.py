"""
Configuration management for Commander backend.

Uses Pydantic Settings for type-safe configuration with .env file support.
"""
import json
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict, Optional

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
    
    # Google Credentials (required)
    google_credentials_json: str = Field(
        default="",
        description="Google OAuth credentials as JSON string"
    )
    
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
    frontend_url: str = Field(default="http://localhost:5173")
    
    @property
    def google_credentials_dict(self) -> Optional[Dict[str, Any]]:
        """
        Get Google credentials as a dictionary.
        
        Parses the GOOGLE_CREDENTIALS_JSON environment variable.
        
        Returns:
            Parsed credentials dictionary or None if not set
        
        Raises:
            ValueError: If credentials are set but cannot be parsed
        """
        if not self.google_credentials_json:
            return None
        try:
            return json.loads(self.google_credentials_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse GOOGLE_CREDENTIALS_JSON: {e}")
    
    def validate_config(self) -> list[str]:
        """Validate configuration and return list of warnings/errors."""
        issues = []
        
        if not self.openai_api_key:
            issues.append("OPENAI_API_KEY is not set")
        
        if not self.qdrant_url:
            issues.append("QDRANT_URL is not set")
        
        if not self.qdrant_api_key:
            issues.append("QDRANT_API_KEY is not set")
        

        try:
            creds = self.google_credentials_dict
            if not creds:
                issues.append(
                    "GOOGLE_CREDENTIALS_JSON is not set. "
                    "Please set the GOOGLE_CREDENTIALS_JSON environment variable."
                )
        except ValueError as e:
            issues.append(f"Failed to parse GOOGLE_CREDENTIALS_JSON: {e}")
        
        # Ensure data directory exists
        if not self.data_dir.exists():
            try:
                self.data_dir.mkdir(parents=True, exist_ok=True)
                print(f"✓ Created data directory: {self.data_dir}")
            except Exception as e:
                issues.append(f"Cannot create data directory {self.data_dir}: {e}")
        
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

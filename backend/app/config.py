# backend/app/config.py

from pydantic_settings import BaseSettings
from pydantic import field_validator, ValidationError
from typing import List
import os
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/screenwriter_db"
    
    # AI Provider: "openai" or "anthropic"
    AI_PROVIDER: str = "anthropic"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    
    # Security
    SECRET_KEY: str = "your-secret-key-replace-in-production"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]
    
    # Rate limiting
    MAX_TOKENS: int = 4000
    MAX_SECTION_LENGTH: int = 1500
    
    # Caching
    CACHE_TTL: int = 900  # 15 minutes

    # Embedding settings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Book processing
    MAX_BOOK_SIZE_MB: int = 50
    CHUNK_SIZE_TOKENS: int = 750
    CHUNK_OVERLAP_TOKENS: int = 150
    MAX_CHUNKS_PER_RETRIEVAL: int = 6
    MAX_CONCEPTS_PER_REVIEW: int = 10
    KG_EXTRACTION_MODEL: str = "gpt-4"

    # Agent settings
    MAX_AGENTS_PER_REVIEW: int = 5
    AGENT_REVIEW_TIMEOUT: int = 90

    # Pipeline composition
    PIPELINE_BATCH_SIZE: int = 5
    PIPELINE_COMPOSITION_MAX_TOKENS: int = 2000

    # Agent pipeline budget
    MAX_AGENTS_PER_PIPELINE_STEP: int = 3
    AGENT_RELEVANCE_THRESHOLD: float = 0.3

    # File storage
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Server
    PORT: int = 8000

    @field_validator('AI_PROVIDER')
    def validate_ai_provider(cls, v):
        if v not in ("openai", "anthropic"):
            raise ValueError("AI_PROVIDER must be 'openai' or 'anthropic'")
        return v
    
    @field_validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if v == "your-secret-key-replace-in-production":
            logger.warning("Using default SECRET_KEY - please change in production!")
        return v
    
    @field_validator('ENVIRONMENT')
    def validate_environment(cls, v):
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set debug based on environment
        if self.ENVIRONMENT == "development":
            self.DEBUG = True
        
        # Validate critical settings in production
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "your-secret-key-replace-in-production":
                raise ValueError("Must set a secure SECRET_KEY in production")
            if any("localhost" in origin for origin in self.ALLOWED_ORIGINS):
                logger.warning("localhost in ALLOWED_ORIGINS for production!")

# Create settings instance
try:
    settings = Settings()
except ValidationError as e:
    logger.error(f"Configuration error: {e}")
    raise

# Export specific settings based on environment
def get_settings() -> Settings:
    return settings

# Development-specific settings
if settings.ENVIRONMENT == "development":
    # Enable more verbose logging
    logging.basicConfig(level=logging.DEBUG)
else:
    # Production logging
    logging.basicConfig(level=logging.INFO)


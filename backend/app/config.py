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
    ANTHROPIC_MODEL: str = "claude-opus-4-8"
    
    # Security
    SECRET_KEY: str = "your-secret-key-replace-in-production"

    # Library admin gate (books roadmap Phase 1.5). The book/agent/snippet
    # library is GLOBAL — readable by every authenticated user — but writable
    # only by the emails listed here (comma-separated). Empty list: writes stay
    # open in development (mock auth) and are locked in production.
    ADMIN_EMAILS: str = ""
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:4321", "http://localhost:3000"]
    
    # Rate limiting
    MAX_TOKENS: int = 4000
    MAX_SECTION_LENGTH: int = 1500

    # Screenplay quality loop (Phase 3): per-scene critique+rewrite and a final
    # whole-screenplay polish pass. Trades ~3x generation tokens for quality;
    # set SCREENPLAY_CRITIQUE_ENABLED=false to fall back to single-pass generation.
    SCREENPLAY_CRITIQUE_ENABLED: bool = True
    SCREENPLAY_CRITIQUE_THRESHOLD: int = 4   # rewrite a scene if any axis scores < this (1-5)
    SCREENPLAY_POLISH_ENABLED: bool = True

    # Craft doctrine (books roadmap Phase 2): inject the format's book concepts
    # into the critique/rewrite/polish loop. Kill-switch for A/B and prod.
    DOCTRINE_IN_GENERATION: bool = True
    DOCTRINE_MAX_CONCEPTS: int = 8
    DOCTRINE_MAX_CHARS: int = 6000   # ~1500 tokens; doctrine must never crowd out the scene
    
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
    MEDIA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Server
    PORT: int = 8000

    # MCP server base URL — metadata only (issuer/resource_server_url in
    # AuthSettings). Static-bearer auth lives in the TokenVerifier and is
    # unaffected by this value. Localhost default keeps local docker compose
    # behavior unchanged; set MCP_BASE_URL to the public host in prod.
    MCP_BASE_URL: str = "http://localhost:8001"

    # MCP DNS-rebinding protection. Validates the inbound Host header for the
    # /mcp endpoint. Disabled by default because the server is API-key-gated and
    # enabling it requires enumerating every allowed client Host. On a public
    # host you may set MCP_DNS_REBINDING_PROTECTION=true to harden the now-public
    # surface — auth (TokenVerifier) is the primary defense either way.
    MCP_DNS_REBINDING_PROTECTION: bool = False

    # Google Cloud (Imagen AI image generation)
    GOOGLE_CLOUD_PROJECT: str = ""
    IMAGEN_MODEL: str = "imagen-3.0-generate-001"
    IMAGEN_REGION: str = "us-central1"

    # vapai-studio integration (Send-to-vapai). Empty VAPAI_MCP_URL disables the
    # feature; the endpoint then returns 424. The screenplay is pushed to vapai's
    # FastMCP HTTP endpoint (Streamable HTTP / JSON-RPC) authenticated with a
    # shared bearer token — no per-user Supabase JWT needed.
    VAPAI_MCP_URL: str = ""            # e.g. http://localhost:8765/mcp
    VAPAI_MCP_API_KEY: str = ""        # Bearer; matches vapai's MCP_API_KEY
    VAPAI_DEFAULT_USER_ID: str = ""    # optional; passed as create_project user_id
    VAPAI_WEB_URL: str = ""            # e.g. http://localhost:3000 — base for deep link
    VAPAI_TIMEOUT_SECONDS: float = 30.0
    VAPAI_PROJECT_TYPE: str = "standalone"  # one of standalone/series/film/short

    @property
    def admin_email_set(self) -> set:
        """Normalized (lowercased, trimmed) admin emails from ADMIN_EMAILS."""
        return {e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()}

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


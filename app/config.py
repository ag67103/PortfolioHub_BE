from pydantic_settings import BaseSettings
from typing import Optional, List
import json
import os

class Settings(BaseSettings):
    # Database settings
    database_url: str = "postgresql://postgres:postgres@localhost:5432/portfolio"
    
    # JWT settings
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Public URL of the frontend (used for share links and link previews)
    frontend_url: str = ""

    # CORS settings - can be set via environment variable as JSON array or comma-separated
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3002", "http://127.0.0.1:3000", "http://127.0.0.1:3002"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # tolerate leftover variables such as MONGODB_URL
    
    @property
    def public_frontend_url(self) -> str:
        if self.frontend_url:
            return self.frontend_url.rstrip('/')
        for origin in self.cors_origins:
            if 'localhost' not in origin and '127.0.0.1' not in origin:
                return origin.rstrip('/')
        return 'http://localhost:3000'

    @property
    def async_database_url(self) -> str:
        """DATABASE_URL as given by the platform (postgres:// or postgresql://), converted for asyncpg."""
        url = self.database_url
        for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url[len(prefix):]
        return url

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Handle CORS_ORIGINS from environment variable
        cors_env = os.getenv("CORS_ORIGINS")
        if cors_env:
            try:
                # Try to parse as JSON array
                self.cors_origins = json.loads(cors_env)
            except json.JSONDecodeError:
                # Fall back to comma-separated values
                self.cors_origins = [origin.strip() for origin in cors_env.split(",")]

settings = Settings()

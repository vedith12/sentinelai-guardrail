import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/guardrail")
    
    # LLM Settings
    OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY", None)
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY", None)
    
    # Default model configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter") # openrouter or gemini
    LLM_MODEL: str = os.getenv("LLM_MODEL", "google/gemma-2-9b-it:free") # e.g. gemini-1.5-flash for gemini
    
    # PII Configuration
    USE_PRESIDIO: bool = os.getenv("USE_PRESIDIO", "false").lower() == "true"

    class Config:
        env_file = ".env"

settings = Settings()

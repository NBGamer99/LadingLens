from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_ID: str = "ladinglens"
    GMAIL_CREDENTIALS_FILE: str = "credentials.json"
    GMAIL_TOKEN_FILE: str = "token.json"

    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:latest"
    ANTHROPIC_API_KEY: Optional[str] = None

    FIRESTORE_COLLECTION_HBL: str = "hbl"
    FIRESTORE_COLLECTION_MBL: str = "mbl"

    class Config:
        env_file = ".env"

settings = Settings()

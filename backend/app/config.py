from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
import os

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

    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def google_creds_path(self) -> Optional[str]:
        if not self.GOOGLE_APPLICATION_CREDENTIALS:
            return None

        path = Path(self.GOOGLE_APPLICATION_CREDENTIALS)
        if path.is_absolute():
            return str(path)

        # Assume relative to project root
        project_root = Path(__file__).parent.parent.parent
        resolved_path = project_root / path
        return str(resolved_path)

settings = Settings()

# Set environment variable for Google SDKs
if settings.google_creds_path:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_creds_path

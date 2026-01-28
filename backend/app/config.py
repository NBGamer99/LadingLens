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
    FIRESTORE_COLLECTION_JOBS: str = "jobs"

    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    def _resolve_path(self, file_path: str) -> str:
        """Resolve a path relative to the project root."""
        path = Path(file_path)
        if path.is_absolute():
            return str(path)
        # Project root is parent of backend (which is parent of app, which is parent of config.py)
        project_root = Path(__file__).parent.parent.parent
        resolved_path = project_root / path
        return str(resolved_path)

    @property
    def gmail_credentials_path(self) -> str:
        return self._resolve_path(self.GMAIL_CREDENTIALS_FILE)

    @property
    def gmail_token_path(self) -> str:
        return self._resolve_path(self.GMAIL_TOKEN_FILE)

    @property
    def google_creds_path(self) -> Optional[str]:
        if not self.GOOGLE_APPLICATION_CREDENTIALS:
            return None
        return self._resolve_path(self.GOOGLE_APPLICATION_CREDENTIALS)

settings = Settings()

# Set environment variable for Google SDKs
if settings.google_creds_path:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_creds_path


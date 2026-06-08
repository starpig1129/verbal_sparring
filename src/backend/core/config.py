from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str
    test_database_url: str = ""
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:12b"
    secret_key: str
    # 7 days; consider shortening and adding a refresh token endpoint for production
    access_token_expire_minutes: int = 10080

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")


settings = Settings()

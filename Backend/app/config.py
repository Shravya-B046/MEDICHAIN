import os
from pathlib import Path
from typing import List
from pydantic import Field
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Fallback if pydantic-settings is not yet installed in current python
    from pydantic import BaseModel as BaseSettings  # type: ignore
    SettingsConfigDict = None  # type: ignore

# Base directory for the backend
BACKEND_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """MEDICHAIN backend application configuration settings."""
    PROJECT_NAME: str = "MEDICHAIN API"
    PROJECT_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # Database Configuration (PostgreSQL default; fallback to SQLite for local tests)
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/medichain"
    )

    # Google Gemini AI API Configuration
    GEMINI_API_KEY: str = Field(default="")

    # CORS Configuration
    CORS_ORIGINS: str = Field(
        default="http://localhost:8081,http://127.0.0.1:8081,http://localhost:8080,http://127.0.0.1:8080,http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000"
    )

    # Temporary File Upload Configuration
    UPLOAD_TEMP_DIR: str = Field(default="uploads")
    MAX_FILE_SIZE_BYTES: int = Field(default=10 * 1024 * 1024)  # 10 MB max
    ALLOWED_EXTENSIONS: str = Field(default="pdf,png,jpg,jpeg")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower().lstrip(".") for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()]

    @property
    def upload_dir_path(self) -> Path:
        path = BACKEND_DIR / self.UPLOAD_TEMP_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=str(BACKEND_DIR / ".env"),
            env_file_encoding="utf-8",
            extra="ignore",
        )

# Instantiate singleton settings
settings = Settings()


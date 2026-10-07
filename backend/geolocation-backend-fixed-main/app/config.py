from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
import json
from pydantic import field_validator

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://apt_vuln_app:Vul%21intern_aepttas@100.112.49.39:5432/aepttas_xdr"
    DATABASE_SCHEMA: str = "apt"
    PLAY_INTEGRITY_MODE: str = "mock"  # "mock" or "real"
    PLAY_INTEGRITY_PACKAGE_NAME: str = "com.example.aeptasshield"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    APK_UPLOAD_DIR: str = "./tmp_apks"
    ALLOWED_CORS_ORIGINS: Union[str, List[str]] = ["*"]
    EXPLANATION_MODE: str = "template"
    LLM_API_KEY: str = ""

    @field_validator("ALLOWED_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                # Try parsing JSON array e.g., ["*"] or ["http://localhost:3000"]
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                # Fallback to comma-separated list
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

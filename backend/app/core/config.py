# OWNER: P1
from typing import List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    DATABASE_URL: str = "sqlite:///./festos.db"
    JWT_SECRET: str = "festos-dev-insecure-secret-key-change-in-production"
    JWT_EXPIRE_MIN: int = 1440
    AUTH_DISABLED: bool = True
    FESTOS_TZ: str = "Asia/Kolkata"
    FESTOS_NOW: Optional[str] = None
    DATA_DIR: str = "./data"
    SEED_ON_START: bool = False
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: Optional[str] = ""
    ACCOM_SOLVER: str = "heuristic"
    SCHED_SOLVER: str = "heuristic"
    QR_SECRET: str = "festos-dev-qr-verification-secret"
    VITE_API_URL: str = "http://localhost:8000"
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            import json
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

settings = Settings()

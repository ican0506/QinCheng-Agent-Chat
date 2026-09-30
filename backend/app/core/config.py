from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout_seconds: float
    llm_max_tokens: int
    llm_temperature: float
    cors_origins: tuple[str, ...]
    session_history_limit: int
    session_limit: int
    profile_extraction_enabled: bool = False
    profile_extraction_timeout_seconds: float = 5

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_model and self.llm_base_url)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        origins = tuple(
            item.strip()
            for item in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if item.strip()
        )
        return cls(
            llm_base_url=os.getenv(
                "LLM_BASE_URL", "https://zhenze-huhehaote.cmecloud.cn/v1"
            ),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", "deepseek-v4-flash-0731"),
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            cors_origins=origins,
            session_history_limit=int(os.getenv("SESSION_HISTORY_LIMIT", "40")),
            session_limit=int(os.getenv("SESSION_LIMIT", "1000")),
            profile_extraction_enabled=os.getenv("PROFILE_EXTRACTION_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
            profile_extraction_timeout_seconds=float(os.getenv("PROFILE_EXTRACTION_TIMEOUT_SECONDS", "5")),
        )

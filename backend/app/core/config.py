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
    final_explanation_timeout_seconds: float = 12
    realtime_policy_search_enabled: bool = False
    realtime_policy_search_provider: str = ''
    realtime_policy_search_api_key: str = ''
    realtime_policy_allowed_domains: tuple[str, ...] = ('suzhou.gov.cn', 'hrss.suzhou.gov.cn')
    realtime_policy_search_timeout_seconds: float = 8
    realtime_policy_search_max_results: int = 5

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
            final_explanation_timeout_seconds=max(0.001, float(os.getenv("FINAL_EXPLANATION_TIMEOUT_SECONDS", "12"))),
            realtime_policy_search_enabled=os.getenv('REALTIME_POLICY_SEARCH_ENABLED', 'false').lower() in {'true','1','yes','on'},
            realtime_policy_search_provider=os.getenv('REALTIME_POLICY_SEARCH_PROVIDER', ''),
            realtime_policy_search_api_key=os.getenv('REALTIME_POLICY_SEARCH_API_KEY', ''),
            realtime_policy_allowed_domains=tuple(d.strip().lower() for d in os.getenv('REALTIME_POLICY_ALLOWED_DOMAINS', 'suzhou.gov.cn,hrss.suzhou.gov.cn').split(',') if d.strip()),
            realtime_policy_search_timeout_seconds=max(0.001, float(os.getenv('REALTIME_POLICY_SEARCH_TIMEOUT_SECONDS', '8'))),
            realtime_policy_search_max_results=max(1, int(os.getenv('REALTIME_POLICY_SEARCH_MAX_RESULTS', '5'))),
        )

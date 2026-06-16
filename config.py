from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:

    llm_provider: str = os.getenv("LLM_PROVIDER", "deepseek")

    # Deepseek API
    deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_base_url: str = os.getenv(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
    )

    # Tavily API
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")

    # Ollama model choice
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")

    # Agent Behavior
    max_search_results: int = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "1"))
    request_timeout_s: int = int(os.getenv("REQUEST_TIMEOUT_S", "45"))


settings = Settings()

if __name__ == "__main__":
    print(settings)
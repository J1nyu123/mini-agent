import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # LLM — 优先从环境变量读取：MINI_AGENT_API_URL / MINI_AGENT_API_KEY
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-3.5-turbo"
    temperature: float = 0.7

    # Memory
    short_term_max_turns: int = 10

    # Harness
    max_retries: int = 3
    retry_delay_ms: int = 200
    tool_timeout_ms: int = 10000

    # Loop
    max_turns: int = 5

    # Search
    search_api_key: str = "" #填入api_key (可选)
    search_api_url: str = "https://tavily.com"

    # Database
    db_path: str = "mini_agent.db"

    def __post_init__(self):
        if not self.llm_api_url:
            self.llm_api_url = os.environ.get("MINI_AGENT_API_URL", "")
        if not self.llm_api_key:
            self.llm_api_key = os.environ.get("MINI_AGENT_API_KEY", "")
        if self.llm_model == "gpt-3.5-turbo":
            self.llm_model = os.environ.get("MINI_AGENT_MODEL", self.llm_model)
        if not self.search_api_key:
            self.search_api_key = os.environ.get("MINI_AGENT_SEARCH_API_KEY", "")
        if not self.search_api_url:
            self.search_api_url = os.environ.get("MINI_AGENT_SEARCH_API_URL", "")

    def is_real_llm(self) -> bool:
        return bool(self.llm_api_url and self.llm_api_key)

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULTS = {
    "jira_project_key": "KAN", "dataset_label": "tyn-release-assessment-v2",
    "jira_issue_type": "Task", "jira_link_type": "Relates",
    "gemini_model": "gemini-2.5-flash",
    "openrouter_model": "meta-llama/llama-3.3-70b-instruct:free",
    "openrouter_base_url": "https://openrouter.ai/api/v1",
    "nvidia_model": "meta/llama-3.3-70b-instruct",
    "nvidia_base_url": "https://integrate.api.nvidia.com/v1",
    "ollama_base_url": "http://localhost:11434",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "ReleasePilot API"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = "KAN"
    dataset_label: str = "tyn-release-assessment-v2"
    jira_issue_type: str = "Task"
    jira_link_type: str = "Relates"
    jira_timeout_seconds: float = 30
    jira_max_retries: int = 3
    jira_retry_backoff_seconds: float = 1.0

    llm_provider_order: str = "gemini,openrouter,nvidia,ollama"
    llm_min_interval_seconds: float = 6.5
    llm_timeout_seconds: float = 120
    llm_provider_cooldown_seconds: float = 90
    llm_max_tokens: int = 4096
    gemini_api_key: str = ""
    gemini_model: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    openrouter_base_url: str = ""
    nvidia_api_key: str = ""
    nvidia_model: str = ""
    nvidia_base_url: str = ""
    ollama_base_url: str = ""
    ollama_model: str = ""

    agent_max_iterations: int = 200
    agent_steps_per_requirement: int = 12
    agent_tool_calls_per_requirement: int = 20
    agent_max_link_depth: int = 4
    agent_max_unique_issues: int = 150
    agent_tool_timeout_seconds: float = 30

    @model_validator(mode="after")
    def _fill_empty(self):
        for k, v in DEFAULTS.items():
            if not getattr(self, k):
                setattr(self, k, v)
        self.jira_base_url = self.jira_base_url.rstrip("/")
        return self


def get_settings() -> Settings:
    return Settings()
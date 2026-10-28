from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    planner: str = "heuristic"  # "heuristic" | "llm"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o-mini"
    openai_api_key: str = ""
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "agentic-web-search-service"
    headless: bool = True
    action_timeout_ms: int = 3000
    host: str = "0.0.0.0"
    port: int = 8000
    max_steps: int = 25


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://nextflow:nextflow@localhost:5432/nextflow"

    # Redis
    redis_url: str = "redis://localhost:6380/0"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # LLM Provider Configuration (D-08, D-09)
    default_provider: str = "openai"
    default_model: str = "gpt-4o"
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # WebSocket
    ws_ping_interval: float = 20.0
    ws_ping_timeout: float = 20.0
    redis_pubsub_prefix: str = "nextflow:ws:events"

    # App
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()

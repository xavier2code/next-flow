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

    # Embedding Configuration (D-22, D-25)
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    # WebSocket
    ws_ping_interval: float = 20.0
    ws_ping_timeout: float = 20.0
    redis_pubsub_prefix: str = "nextflow:ws:events"

    # App
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    # MinIO Configuration
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "nextflow"
    minio_secret_key: str = "nextflow123"
    minio_secure: bool = False
    minio_bucket: str = "skill-packages"

    # Skill Sandbox Configuration
    skill_sandbox_memory: str = "256m"
    skill_sandbox_cpus: float = 1.0
    skill_sandbox_timeout: float = 30.0
    skill_sandbox_pids_limit: int = 100
    skill_health_check_interval: float = 30.0


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded and validated once at startup.

    Pydantic-settings reads matching environment variables (case-insensitive)
    and validates their types immediately. If GROQ_API_KEY is missing, the
    app fails to even start — instead of failing three hours into an audit
    run when the first LLM call finally happens.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    groq_api_key: str
    database_url: str
    environment: str = "development"
    log_level: str = "INFO"


settings = Settings()

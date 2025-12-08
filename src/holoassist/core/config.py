from pydantic import BaseModel
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseModel):
    dsn: str | None = None


class RedisSettings(BaseModel):
    url: str | None = None


class LLMSettings(BaseModel):
    chat_service: str | None = None
    reason_service: str | None = None
    ollama_base_url: str | None = None
    deepseek_api_key: str | None = None


class Settings(BaseSettings):
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    llm: LLMSettings = LLMSettings()
    secret_key: str | None = None

    class Config:
        env_nested_delimiter = "__"
        env_file = ".env"
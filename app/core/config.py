"""config with settings classes"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from loguru import logger

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
print(ENV_PATH)


class DBSettings(BaseSettings):
    """setting class for database config"""

    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def DB_URL(self) -> str:
        """get and validate postgres database url"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


class BotSettings(BaseSettings):
    BOT_TOKEN: str

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class LLMSettings(BaseSettings):
    OPENAI_API_KEY: str = Field(alias="openai_api_key")

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


bot_settings = BotSettings()
db_settings = DBSettings()
llm_settings = LLMSettings()

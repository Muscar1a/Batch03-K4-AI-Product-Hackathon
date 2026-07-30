"""Configuration module for OdysseyBot using Pydantic Settings."""

from pathlib import Path
from typing import List, Optional
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Personal Discord Bot
    DISCORD_BOT_TOKEN: Optional[SecretStr] = Field(default=None)
    PERSONAL_DISCORD_GUILD_ID: Optional[str] = Field(default=None)
    PERSONAL_DISCORD_STAFF_CHANNEL_ID: Optional[str] = Field(default=None)
    PERSONAL_DISCORD_ADMIN_ROLE_IDS: List[str] = Field(default_factory=list)

    # Exporter Sidecar (Program Server)
    DCE_SYNC_ENABLED: bool = Field(default=False)
    DCE_USER_TOKEN: Optional[SecretStr] = Field(default=None)
    DCE_SOURCE_GUILD_ID: Optional[str] = Field(default=None)
    DCE_FORUM_CHANNEL_IDS: List[str] = Field(default_factory=list)
    DCE_STATIC_THREAD_MANIFEST: Optional[Path] = Field(default=None)
    DCE_EXPORTER_PATH: str = Field(default="discord-chat-exporter-cli")
    DCE_DAILY_TIME: str = Field(default="17:30")
    DCE_FULL_SYNC_DAY: str = Field(default="sunday")
    DCE_FULL_SYNC_TIME: str = Field(default="02:00")
    DCE_MAX_PARALLEL: int = Field(default=2)
    DCE_TIMEOUT_SECONDS: int = Field(default=1800)

    # LLM & Web API Keys
    GEMINI_API_KEY: Optional[SecretStr] = Field(default=None)
    AI_MODEL: str = Field(default="gemma-4-26b-a4b-it")
    TAVILY_API_KEY: Optional[SecretStr] = Field(default=None)
    FIRECRAWL_API_KEY: Optional[SecretStr] = Field(default=None)

    # Database & Storage
    DATABASE_PATH: Path = Field(default=Path("data/runtime/odysseybot.sqlite3"))
    DIGEST_TIME: str = Field(default="18:00")
    TZ: str = Field(default="Asia/Ho_Chi_Minh")
    DATA_RETENTION_DAYS: int = Field(default=90)
    EXPORT_RETENTION_DAYS: int = Field(default=7)
    LOG_LEVEL: str = Field(default="INFO")

    @model_validator(mode="after")
    def validate_tokens_and_sync(self) -> "Settings":
        if self.DCE_SYNC_ENABLED:
            if not self.DCE_USER_TOKEN or not self.DCE_USER_TOKEN.get_secret_value():
                raise ValueError("DCE_USER_TOKEN is required when DCE_SYNC_ENABLED=true")
            if not self.DCE_SOURCE_GUILD_ID:
                raise ValueError("DCE_SOURCE_GUILD_ID is required when DCE_SYNC_ENABLED=true")

        if self.DISCORD_BOT_TOKEN and self.DCE_USER_TOKEN:
            bot_val = self.DISCORD_BOT_TOKEN.get_secret_value()
            dce_val = self.DCE_USER_TOKEN.get_secret_value()
            if bot_val and dce_val and bot_val == dce_val:
                raise ValueError("DISCORD_BOT_TOKEN and DCE_USER_TOKEN must not be identical")

        return self


settings = Settings()

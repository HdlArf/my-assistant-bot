"""Configuration loader for the bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Central configuration for the bot."""

    # Required
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Optional
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")

    # Database
    DB_PATH: Path = BASE_DIR / "data" / "assistant.db"

    @classmethod
    def validate(cls) -> None:
        """Ensure required settings are present."""
        if not cls.BOT_TOKEN:
            raise ValueError(
                "BOT_TOKEN is missing. "
                "Please set it in your .env file. "
                "Get one from @BotFather on Telegram."
            )


config = Config()

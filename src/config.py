# /config/__init__.py
import sys
from pathlib import Path
from functools import lru_cache
from typing import ClassVar
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger

class APIConfig(BaseSettings):
    # Generic
    APP_AUTHOR: ClassVar[str] = "JakobKB"
    APP_NAME: ClassVar[str] = "RowIO"

    # Sqlite
    STORAGE_DIR: Path = Path(__file__).parent.parent / "temp"
    DB_PATH: Path = STORAGE_DIR / "rowio.db"

    # Video Constants
    VIDEO_WIDTH: ClassVar[int] = 1920
    VIDEO_HEIGHT: ClassVar[int] = 1080
    VIDEO_FPS: ClassVar[int] = 30

    # Other
    # LOG_LEVEL: Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"]

    # pydantic-settings v2 main settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

@lru_cache()
def get_api_config() -> APIConfig:
    return APIConfig()

# Logger
logger.remove()
logger.add(
    sys.stdout,
    filter=lambda rec: rec["level"].name == "CRITICAL",
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <red>{level: <8}</red> | <white>{message}</white>",
)
logger.add(
    sys.stdout,
    filter=lambda rec: rec["level"].name != "CRITICAL",
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
)

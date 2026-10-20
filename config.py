import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: str = ""
    ADMIN_IDS: str = "123456789"
    
    # Growth & Marketing: Telegram Force Join
    FORCE_JOIN_CHANNELS: str = "@YourChannel"
    FORCE_JOIN_LINKS: str = "https://t.me/YourChannel"
    
    # Growth & Marketing: Instagram
    INSTAGRAM_PAGE_URL: str = "https://instagram.com/YourPage"
    INSTAGRAM_USERNAME: str = "YourPage"
    DAILY_INSTAGRAM_CODE: str = "OCR2026"
    INSTAGRAM_BONUS_CREDITS: int = 20
    
    # Referral Program
    REFERRAL_BONUS_CREDITS: int = 10
    DEFAULT_USER_CREDITS: int = 15
    
    # OCR Engine Settings
    TESSERACT_CMD: str = "tesseract"
    DEFAULT_OCR_LANG: str = "fas+eng"
    MAX_PDF_PAGES: int = 25
    
    # Web & Mini App
    WEB_HOST: str = "0.0.0.0"
    WEB_PORT: int = 8000
    DATABASE_PATH: str = "ocr_bot.db"
    
    # Environment
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_id_list(self) -> List[int]:
        ids = []
        for x in self.ADMIN_IDS.split(","):
            cleaned = x.strip()
            if cleaned.isdigit():
                ids.append(int(cleaned))
        return ids

    @property
    def force_channel_list(self) -> List[str]:
        return [c.strip() for c in self.FORCE_JOIN_CHANNELS.split(",") if c.strip()]

settings = Settings()

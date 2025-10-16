from pydantic_settings import BaseSettings
from pydantic import Field

def _parse_triggers(v: str | None) -> set[str]:
    if not v: return {"color_mksysrr6"}  # default: Statut
    return {p.strip() for p in v.split(",") if p.strip()}

class Settings(BaseSettings):
    MONDAY_API_TOKEN: str
    MONDAY_SIGNING_SECRET: str | None = None   # leave empty to skip verify
    BOARD_ID: int
    DATABASE_URL: str                          # postgresql+psycopg://USER:PASS@HOST:5432/DBNAME
    TRIGGER_COLUMN_IDS: set[str] = Field(default_factory=set)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
# allow comma-separated TRIGGER_COLUMN_IDS in .env
if not settings.TRIGGER_COLUMN_IDS:
    import os
    settings.TRIGGER_COLUMN_IDS = _parse_triggers(os.getenv("TRIGGER_COLUMN_IDS"))

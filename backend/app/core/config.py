import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Explicitly search and load .env from backend/ and root directories
_current_dir = Path(__file__).resolve().parent  # app/core
_backend_dir = _current_dir.parent.parent       # backend/
_root_dir = _backend_dir.parent                 # Krisis-AI/

_env_candidates = [
    _backend_dir / ".env",
    _root_dir / ".env",
    _backend_dir / ".env.txt",
    _root_dir / ".env.txt",
]

for _env_file in _env_candidates:
    if _env_file.is_file():
        load_dotenv(dotenv_path=_env_file, override=True)
        break
else:
    load_dotenv()


class Settings(BaseModel):
    PROJECT_NAME: str = "Krisis AI - Damage Mapper"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "*"]
    
    # Thresholds
    SPATIAL_CLUSTER_RADIUS_METERS: float = 50.0
    VISUAL_CONFIDENCE_THRESHOLD: float = 0.50
    DEEPFAKE_THRESHOLD: float = 0.85
    ROUTE_PROXIMITY_THRESHOLD_METERS: float = 75.0

    # Telegram bot configuration (clean any quotes or whitespace)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip("'\"")

    # Default Houston reference coordinates (frontend map viewport)
    DEFAULT_LATITUDE: float = 29.7604
    DEFAULT_LONGITUDE: float = -95.3698


settings = Settings()

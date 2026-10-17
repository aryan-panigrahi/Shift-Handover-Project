"""
Application configuration for Shift Handover Briefing.
"""

import os
from pathlib import Path
from typing import List
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
SEEDED_DIR = DATA_DIR / "seeded_bundle"
UPLOADS_DIR = DATA_DIR / "uploads"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SEEDED_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    app_title: str = "Shift Handover Briefing"
    version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "true").lower() in ("true", "1")
    port: int = int(os.getenv("PORT", "8000"))
    host: str = os.getenv("HOST", "0.0.0.0")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    cors_origins: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:8000,http://127.0.0.1:8000"
        ).split(",")
        if origin.strip()
    ]

    # SQLite
    database_path: str = os.getenv("DATABASE_PATH", str(DATA_DIR / "shift_handover.db"))

    # AMD Cloud / ROCm Model Serving Endpoint
    amd_endpoint_url: str = os.getenv("AMD_ENDPOINT_URL", "").strip()
    amd_api_key: str = os.getenv("AMD_API_KEY", "").strip()
    amd_model_id: str = os.getenv("AMD_MODEL_ID", "meta-llama/Llama-3.1-70B-Instruct")
    amd_accelerator_label: str = os.getenv(
        "AMD_ACCELERATOR_LABEL",
        "AMD ROCm (hardware not verified)"
    )

    # Transcription
    transcription_adapter: str = os.getenv("TRANSCRIPTION_ADAPTER", "mock_whisper")
    transcription_endpoint_url: str = os.getenv("TRANSCRIPTION_ENDPOINT_URL", "").strip()
    transcription_api_key: str = os.getenv("TRANSCRIPTION_API_KEY", "").strip()
    transcription_model_id: str = os.getenv("TRANSCRIPTION_MODEL_ID", "whisper-1")


settings = Settings()

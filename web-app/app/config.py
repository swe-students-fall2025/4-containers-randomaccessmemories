"""Configuration from environment variables."""

import os


class Config:
    """Application configuration."""

    # MongoDB
    MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
    MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
    MONGO_DB = os.getenv("MONGO_DB", "audio_notes")
    MONGO_USER = os.getenv("MONGO_USER", "admin")
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "adminpassword")
    MONGO_URI = (
        f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@"
        f"{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"
    )

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

    # Processing
    PROCESS_INLINE = os.getenv("PROCESS_INLINE", "false").lower() == "true"
    MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "10"))

    # Flask
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Affiliate Content Engine"
    app_env: str = "development"
    app_debug: bool = True

    database_url: str = "postgresql+psycopg://postgres:root@localhost:5432/affiliate_engine"

    storage_path: str = "./storage"
    default_language: str = "id-ID"
    default_video_width: int = 1080
    default_video_height: int = 1920

    ai_provider: str = "openrouter"

    openrouter_api_key: str = ""
    openrouter_model: str = "liquid/lfm-2.5-2.6b:free"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    pexels_api_key: str = ""

    ffmpeg_path: str = "ffmpeg"

    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    app_base_url: str = "http://localhost:8000"


settings = Settings()

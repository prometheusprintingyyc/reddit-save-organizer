from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_redirect_uri: str = "http://localhost:8080/auth/callback"
    gemini_api_key: str = ""
    sync_interval_hours: int = 6
    database_path: str = "/data/redditsave.db"

settings = Settings()

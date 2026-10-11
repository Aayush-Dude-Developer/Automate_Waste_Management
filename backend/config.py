import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_BACKEND: str = "local" # 'firestore' or 'local'
    GOOGLE_CLOUD_PROJECT: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    DEFAULT_RESTAURANT_ID: str = "taiken_kharadi"
    
    class Config:
        env_file = ".env" if os.path.exists(".env") else "../.env"
        extra = "ignore"

settings = Settings()

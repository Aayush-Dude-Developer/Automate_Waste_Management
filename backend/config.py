from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_BACKEND: str = "local" # 'firestore' or 'local'
    GOOGLE_CLOUD_PROJECT: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    DEFAULT_RESTAURANT_ID: str = "taiken_kharadi"
    ALLOWED_USER_EMAILS: str = ""
    
    class Config:
        env_file = "../.env"
        extra = "ignore"

settings = Settings()

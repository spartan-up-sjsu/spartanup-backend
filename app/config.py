import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mysecret")
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    CLOUDINARY_URL: str

    # ... other config variables

    class Config:
        env_file = ".env"


settings = Settings()

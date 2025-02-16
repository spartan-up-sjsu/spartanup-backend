import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mysecret")
    # ... other config variables

    class Config:
        env_file = ".env"


settings = Settings()

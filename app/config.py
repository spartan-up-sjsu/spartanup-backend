import os
from pydantic_settings import BaseSettings
from pymongo import MongoClient
import cloudinary
import cloudinary.uploader
import cloudinary.api


class Settings(BaseSettings):
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mysecret")
    # ... other config variables

    class Config:
        env_file = ".env"


settings = Settings()
client = MongoClient(settings.MONGO_URI)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

db = client.spartan_up
items_collection = db.items

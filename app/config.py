import os
from pydantic_settings import BaseSettings
from pymongo import MongoClient
import cloudinary
import cloudinary.uploader
import cloudinary.api


class Settings(BaseSettings):
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mysecret")
    CLOUDINARY_URL: str | None = os.getenv("CLOUDINARY_URL")
    CLOUDINARY_CLOUD_NAME: str | None = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str | None = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str | None = os.getenv("CLOUDINARY_API_SECRET")

    class Config:
        env_file = ".env"


settings = Settings()
client = MongoClient(settings.MONGO_URI)

# Configure Cloudinary using URL if available, otherwise use individual credentials
if settings.CLOUDINARY_URL:
    cloudinary.config(cloud_name=settings.CLOUDINARY_URL)
else:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
    )

db = client.spartan_up
items_collection = db.items

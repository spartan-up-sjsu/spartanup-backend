import os
from pydantic_settings import BaseSettings
from pymongo import MongoClient
import cloudinary
import cloudinary.uploader
import cloudinary.api
import certifi
import logging


class Settings(BaseSettings):
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "mysecret")
    CLOUDINARY_URL: str | None = os.getenv("CLOUDINARY_URL")
    CLOUDINARY_CLOUD_NAME: str | None = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str | None = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str | None = os.getenv("CLOUDINARY_API_SECRET")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/google/callback"
    )
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "mysecret")
    FRONTEND_CALLBACK_URL: str
    ENV: str = os.getenv("ENV", "development")
    DOMAIN: str = os.getenv("DOMAIN", "localhost")

    class Config:
        env_file = ".env"


settings = Settings()
client = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())


async def upload_image(image_data: bytes) -> str:
    result = cloudinary.uploader.upload(image_data)
    return result["secure_url"]


cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("spartan-up (backend)")

db = client.spartan_up
items_collection = db.items
user_collection = db.users
reviews_collection = db.reviews
conversations_collection = db.conversations
messages_collection = db.messages
reports_collection = db.reports
cookies_collection = db.cookies

print("Logging level set to DEBUG. All logs will be displayed.")

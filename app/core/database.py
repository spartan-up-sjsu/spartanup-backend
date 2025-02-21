from pymongo import MongoClient
from ..config import settings  # Adjust import if necessary

client = MongoClient(settings.MONGO_URI)

try:
    client.admin.command("ping")
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    
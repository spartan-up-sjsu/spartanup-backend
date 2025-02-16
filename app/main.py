from fastapi import FastAPI
from app.routers import auth, users, items
from app.config import Settings
import dotenv

dotenv.load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(title="SJSU Marketplace Backend")
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])
    app.include_router(users.router, prefix="/users", tags=["Users"])
    app.include_router(items.router, prefix="/items", tags=["Items"])
    return app


app = create_app()

# to start: uvicorn app.main:app --reload

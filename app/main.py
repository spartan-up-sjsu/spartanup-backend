from fastapi import FastAPI
from app.routers import (
    auth,
    users,
    items,
    marketplace,
    api,
    reports,
    admin,
    websocket,
    conversation,
    reviews,
    preferences,
)
from app.config import Settings
import dotenv
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(title="SJSU Marketplace Backend")
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])
    app.include_router(users.router, prefix="/users", tags=["Users"])
    app.include_router(items.router, prefix="/items", tags=["Items"])
    app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
    app.include_router(websocket.router, prefix="/ws", tags=["ws"])
    app.include_router(
        conversation.router, prefix="/conversations", tags=["conversations"]
    )
    app.include_router(marketplace.router, prefix="/marketplace", tags=["Marketplace"])
    app.include_router(reports.router, prefix="/reports", tags={"Reports"})
    app.include_router(admin.router, prefix="/admin", tags={"Admin"})
    app.include_router(api.router, prefix="/api", tags=["Api"])
    app.include_router(preferences.router, prefix="/preferences", tags=["Preferences"])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8000",
            "https://spartanup.app",
            "https://www.spartanup.app",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "HEAD", "OPTIONS", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Access-Control-Allow-Headers",
            "Content-Type",
            "Authorization",
            "Access-Control-Allow-Origin",
        ],
    )

    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        html_content = """
        <!DOCTYPE html>
        <html>
          <head>
            <title>Login with Google</title>
          </head>
          <body>
            <h1>Welcome to SJSU Marketplace Backend</h1>
            <a href="/auth/google/login">
              <button type="button">Login with Google</button>
            </a>
          </body>
        </html>
        """

        return html_content

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)

# to start: uvicorn app.main:app --reload --host localhost --port 8000


# to start: uvicorn app.main:app --reload --host localhost --port $PORT

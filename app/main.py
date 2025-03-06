from fastapi import FastAPI
from app.routers import auth, users, items, websocket, conversation
from app.config import Settings
import dotenv
from fastapi.responses import HTMLResponse

dotenv.load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(title="SJSU Marketplace Backend")
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])
    app.include_router(users.router, prefix="/users", tags=["Users"])
    app.include_router(items.router, prefix="/items", tags=["Items"])
    app.include_router(websocket.router, prefix = "/ws", tags=["ws"])
    app.include_router(conversation.router, prefix="/convo", tags=["convo"])

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

# to start: uvicorn app.main:app --reload

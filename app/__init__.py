from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app() -> FastAPI:
    application = FastAPI(title="LLM Convo")
    application.mount(
        "/static",
        StaticFiles(directory=BASE_DIR / "static"),
        name="static",
    )
    from .routes import router

    application.include_router(router)
    return application

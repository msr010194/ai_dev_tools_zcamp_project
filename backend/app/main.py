from fastapi import FastAPI

from app.repositories.memory import InMemoryStore
from app.routers import collections, health, notes, tags
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a new app with its own settings and a fresh in-memory store on `app.state`."""
    settings = settings if settings is not None else Settings()
    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.store = InMemoryStore()
    app.include_router(health.router)
    app.include_router(collections.router)
    app.include_router(tags.router)
    app.include_router(notes.router)
    return app


app = create_app()

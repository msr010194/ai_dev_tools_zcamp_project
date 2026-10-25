import tomllib
from pathlib import Path

from fastapi import FastAPI

from app.errors import register_error_handlers
from app.repositories.memory import InMemoryStore
from app.routers import collections, health, notes, resurface, tags, timeline
from app.settings import Settings

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def project_version() -> str:
    """The backend version from `pyproject.toml`, used as the API version in the OpenAPI spec."""
    with _PYPROJECT.open("rb") as file:
        return tomllib.load(file)["project"]["version"]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a new app with its own settings and a fresh in-memory store on `app.state`."""
    settings = settings if settings is not None else Settings()
    app = FastAPI(title=settings.app_name, version=project_version())
    app.state.settings = settings
    app.state.store = InMemoryStore()
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(collections.router)
    app.include_router(tags.router)
    app.include_router(notes.router)
    app.include_router(timeline.router)
    app.include_router(resurface.router)
    return app


app = create_app()

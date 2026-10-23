"""FastAPI dependencies that hand the app's settings and store to route handlers."""

from fastapi import Request

from app.repositories.memory import InMemoryStore
from app.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> InMemoryStore:
    return request.app.state.store

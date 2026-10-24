"""FastAPI dependencies that hand the app's settings and store to route handlers."""

from typing import Annotated

from fastapi import Depends, Request

from app.repositories.memory import InMemoryStore
from app.services.collections import CollectionService
from app.services.tags import TagService
from app.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> InMemoryStore:
    return request.app.state.store


def get_collection_service(
    store: Annotated[InMemoryStore, Depends(get_store)],
) -> CollectionService:
    return CollectionService(store.collections, store.notes)


def get_tag_service(
    store: Annotated[InMemoryStore, Depends(get_store)],
) -> TagService:
    return TagService(store.tags)

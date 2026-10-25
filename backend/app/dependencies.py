"""FastAPI dependencies that hand the app's settings, store, clock and random source to route handlers."""

import random
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request

from app.repositories.memory import InMemoryStore
from app.services.collections import CollectionService
from app.services.notes import NoteService
from app.services.resurface import RandomSource, ResurfaceService
from app.services.tags import TagService
from app.services.timeline import TimelineService
from app.settings import Settings

Clock = Callable[[], datetime]


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> InMemoryStore:
    return request.app.state.store


def _utc_now() -> datetime:
    return datetime.now(UTC)


def get_clock() -> Clock:
    """The app's notion of "now"; tests override it via `app.dependency_overrides`."""
    return _utc_now


def get_random() -> RandomSource:
    """A fresh OS-seeded generator per request; tests override it with a seeded one."""
    return random.Random()


def get_collection_service(
    store: Annotated[InMemoryStore, Depends(get_store)],
) -> CollectionService:
    return CollectionService(store.collections, store.notes)


def get_tag_service(
    store: Annotated[InMemoryStore, Depends(get_store)],
) -> TagService:
    return TagService(store.tags)


def get_note_service(
    store: Annotated[InMemoryStore, Depends(get_store)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> NoteService:
    return NoteService(store.notes, store.collections, store.tags, clock=clock)


def get_timeline_service(
    store: Annotated[InMemoryStore, Depends(get_store)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TimelineService:
    return TimelineService(
        store.notes, store.collections, store.tags, cursor_key=settings.cursor_secret.encode()
    )


def get_resurface_service(
    store: Annotated[InMemoryStore, Depends(get_store)],
    random_source: Annotated[RandomSource, Depends(get_random)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> ResurfaceService:
    return ResurfaceService(store.notes, random_source, clock)

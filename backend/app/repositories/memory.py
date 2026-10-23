"""In-memory repository implementation and the store that holds the app's repositories."""

import builtins
from collections.abc import Hashable
from copy import deepcopy
from typing import Any

from app.models.collection import Collection
from app.repositories.base import Identifiable, Repository


class InMemoryRepository[T: Identifiable](Repository[T]):
    """Keeps entities in an instance-level dict, storing and returning copies."""

    def __init__(self) -> None:
        self._items: dict[Hashable, T] = {}

    def get(self, id: Hashable) -> T | None:
        entity = self._items.get(id)
        return deepcopy(entity) if entity is not None else None

    def list(self) -> builtins.list[T]:
        return [deepcopy(entity) for entity in self._items.values()]

    def add(self, entity: T) -> T:
        if entity.id in self._items:
            raise ValueError(f"Entity with id {entity.id!r} already exists")
        self._items[entity.id] = deepcopy(entity)
        return deepcopy(entity)

    def update(self, entity: T) -> T | None:
        if entity.id not in self._items:
            return None
        self._items[entity.id] = deepcopy(entity)
        return deepcopy(entity)

    def delete(self, id: Hashable) -> bool:
        return self._items.pop(id, None) is not None


class InMemoryStore:
    """Holds one app's in-memory repositories; created per app by `create_app()`.

    Domain tasks add one repository attribute per entity here.
    """

    def __init__(self) -> None:
        self.collections: InMemoryRepository[Collection] = InMemoryRepository()
        # Stays empty until the Note entity exists; anything stored here must have a `collection_id`.
        self.notes: InMemoryRepository[Any] = InMemoryRepository()

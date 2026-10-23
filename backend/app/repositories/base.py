"""Generic, storage-agnostic repository interface."""

import builtins
from abc import ABC, abstractmethod
from collections.abc import Hashable
from typing import Protocol


class Identifiable(Protocol):
    """Any entity that exposes an `id`."""

    @property
    def id(self) -> Hashable: ...


class Repository[T: Identifiable](ABC):
    """CRUD access to entities of type `T`, independent of how they are stored.

    `list()` order is not part of the contract; callers that need an order must sort.
    """

    @abstractmethod
    def get(self, id: Hashable) -> T | None:
        """Return the entity with `id`, or `None` if there is none."""

    @abstractmethod
    def list(self) -> builtins.list[T]:
        """Return all entities."""

    @abstractmethod
    def add(self, entity: T) -> T:
        """Store a new entity and return it; raise `ValueError` if its id already exists."""

    @abstractmethod
    def update(self, entity: T) -> T | None:
        """Replace the entity with the same id and return it, or `None` if there is none."""

    @abstractmethod
    def delete(self, id: Hashable) -> bool:
        """Remove the entity with `id`; return whether it existed."""

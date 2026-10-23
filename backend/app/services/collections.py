"""Collection use cases: the tree view and the add/rename/move/delete rules."""

import uuid
from collections.abc import Callable
from typing import Protocol

from app.models.collection import Collection
from app.repositories.base import Identifiable, Repository
from app.schemas.collections import CollectionTree


class CollectionMember(Identifiable, Protocol):
    """Anything filed in a collection (e.g. a note)."""

    @property
    def collection_id(self) -> str | None: ...


class CollectionError(Exception):
    """Base class for collection rule violations; `str(error)` is the client-facing message."""

    message = "Collection error"

    def __init__(self) -> None:
        super().__init__(self.message)


class CollectionNotFoundError(CollectionError):
    message = "Collection not found"


class ParentCollectionNotFoundError(CollectionError):
    message = "Parent collection not found"


class CollectionCycleError(CollectionError):
    message = "A collection cannot be moved under itself or one of its descendants"


class DuplicateCollectionNameError(CollectionError):
    message = "A collection with that name already exists here"


class CollectionNotEmptyError(CollectionError):
    message = "Collection is not empty. Move or delete its contents first."


def _sort_key(collection: Collection) -> tuple[str, str]:
    return collection.name.casefold(), collection.id


class CollectionService:
    def __init__(
        self,
        collections: Repository[Collection],
        notes: Repository[CollectionMember],
        id_factory: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self._collections = collections
        self._notes = notes
        self._new_id = id_factory

    def list_tree(self) -> list[CollectionTree]:
        """Build the nested tree without recursion, so arbitrarily deep chains work."""
        collections = sorted(self._collections.list(), key=_sort_key)
        nodes: dict[str, CollectionTree] = {
            c.id: {"id": c.id, "name": c.name, "parent_id": c.parent_id, "children": []}
            for c in collections
        }
        roots: list[CollectionTree] = []
        for collection in collections:
            node = nodes[collection.id]
            if collection.parent_id is None:
                roots.append(node)
            elif collection.parent_id in nodes:
                nodes[collection.parent_id]["children"].append(node)
        return roots

    def create(self, name: str, parent_id: str | None = None) -> Collection:
        self._require_parent(parent_id)
        self._require_unique_name(name, parent_id, exclude_id=None)
        return self._collections.add(Collection(id=self._new_id(), name=name, parent_id=parent_id))

    def update(
        self,
        collection_id: str,
        *,
        name: str | None = None,
        move: bool = False,
        parent_id: str | None = None,
    ) -> Collection:
        """Rename (when `name` is given) and/or move (when `move` is true) in one step.

        Every rule is checked before anything is written.
        """
        collection = self._require(collection_id)
        new_name = name if name is not None else collection.name
        new_parent_id = parent_id if move else collection.parent_id
        if move:
            self._require_parent(new_parent_id)
            if self._is_self_or_descendant(new_parent_id, collection_id):
                raise CollectionCycleError()
        self._require_unique_name(new_name, new_parent_id, exclude_id=collection_id)
        updated = collection.model_copy(update={"name": new_name, "parent_id": new_parent_id})
        result = self._collections.update(updated)
        if result is None:
            raise CollectionNotFoundError()
        return result

    def delete(self, collection_id: str) -> None:
        self._require(collection_id)
        has_children = any(c.parent_id == collection_id for c in self._collections.list())
        has_notes = any(n.collection_id == collection_id for n in self._notes.list())
        if has_children or has_notes:
            raise CollectionNotEmptyError()
        self._collections.delete(collection_id)

    def _require(self, collection_id: str) -> Collection:
        collection = self._collections.get(collection_id)
        if collection is None:
            raise CollectionNotFoundError()
        return collection

    def _require_parent(self, parent_id: str | None) -> None:
        if parent_id is not None and self._collections.get(parent_id) is None:
            raise ParentCollectionNotFoundError()

    def _require_unique_name(self, name: str, parent_id: str | None, exclude_id: str | None) -> None:
        folded = name.casefold()
        for sibling in self._collections.list():
            if (
                sibling.parent_id == parent_id
                and sibling.id != exclude_id
                and sibling.name.casefold() == folded
            ):
                raise DuplicateCollectionNameError()

    def _is_self_or_descendant(self, candidate_id: str | None, ancestor_id: str) -> bool:
        """Whether `candidate_id` is `ancestor_id` or lies somewhere below it."""
        parent_of = {c.id: c.parent_id for c in self._collections.list()}
        seen: set[str] = set()
        current = candidate_id
        while current is not None and current not in seen:
            if current == ancestor_id:
                return True
            seen.add(current)
            current = parent_of.get(current)
        return False

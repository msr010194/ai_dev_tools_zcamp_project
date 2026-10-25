"""Business rules for notes: each sits in exactly one existing collection and only uses existing tags."""

import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from app.models.collection import Collection
from app.models.note import NOTE_CLASSES, Note, NoteType, type_fields
from app.models.tag import Tag
from app.repositories.base import Repository

_SHARED_UPDATABLE_FIELDS = frozenset({"body", "collection_id", "tag_ids"})


class NoteError(Exception):
    message = "Note error"

    def __init__(self) -> None:
        super().__init__(self.message)


class NoteNotFoundError(NoteError):
    message = "Note not found"


class NoteCollectionNotFoundError(NoteError):
    message = "Collection not found"


class NoteTagNotFoundError(NoteError):
    message = "Tag not found"


class DuplicateTagIdError(NoteError):
    message = "Duplicate tag id"


class NoteTypeChangeError(NoteError):
    message = "Note type cannot be changed"


class EmptyNoteUpdateError(NoteError):
    message = "At least one field must be provided"


class FieldNotAllowedError(NoteError):
    message = "Field not allowed for this note type"


class NoteService:
    def __init__(
        self,
        notes: Repository[Note],
        collections: Repository[Collection],
        tags: Repository[Tag],
        id_factory: Callable[[], str] = lambda: str(uuid.uuid4()),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._notes = notes
        self._collections = collections
        self._tags = tags
        self._id_factory = id_factory
        self._clock = clock

    def get(self, note_id: str) -> Note:
        note = self._notes.get(note_id)
        if note is None:
            raise NoteNotFoundError()
        return note

    def create(
        self,
        note_type: NoteType,
        body: str,
        collection_id: str,
        tag_ids: Sequence[str],
        fields: Mapping[str, Any] | None = None,
    ) -> Note:
        """Create a note; `fields` holds the Type-specific values that were sent (omitted ones use defaults)."""
        fields = dict(fields or {})
        if not set(fields) <= type_fields(note_type):
            raise FieldNotAllowedError()
        self._require_collection(collection_id)
        self._check_tags(tag_ids)
        note = NOTE_CLASSES[note_type](
            id=self._id_factory(),
            body=body,
            collection_id=collection_id,
            tag_ids=list(tag_ids),
            created_at=self._clock(),
            **fields,
        )
        return self._notes.add(note)

    def update(self, note_id: str, changes: Mapping[str, Any]) -> Note:
        """Apply only the fields present in `changes`; everything is checked before anything is saved."""
        if not changes:
            raise EmptyNoteUpdateError()
        note = self.get(note_id)
        if "type" in changes and changes["type"] != note.type:
            raise NoteTypeChangeError()
        updates = {name: value for name, value in changes.items() if name != "type"}
        if not set(updates) <= _SHARED_UPDATABLE_FIELDS | type_fields(note.type):
            raise FieldNotAllowedError()
        if "collection_id" in updates:
            self._require_collection(updates["collection_id"])
        if "tag_ids" in updates:
            self._check_tags(updates["tag_ids"])
            updates["tag_ids"] = list(updates["tag_ids"])
        updated = type(note).model_validate({**note.model_dump(), **updates})
        stored = self._notes.update(updated)
        if stored is None:
            raise NoteNotFoundError()
        return stored

    def delete(self, note_id: str) -> None:
        if not self._notes.delete(note_id):
            raise NoteNotFoundError()

    def _require_collection(self, collection_id: str) -> None:
        if self._collections.get(collection_id) is None:
            raise NoteCollectionNotFoundError()

    def _check_tags(self, tag_ids: Sequence[str]) -> None:
        if len(set(tag_ids)) != len(tag_ids):
            raise DuplicateTagIdError()
        for tag_id in tag_ids:
            if self._tags.get(tag_id) is None:
                raise NoteTagNotFoundError()

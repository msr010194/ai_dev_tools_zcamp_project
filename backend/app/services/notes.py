"""Business rules for notes: each sits in exactly one existing collection and only uses existing tags."""

import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from app.models.collection import Collection
from app.models.note import NOTE_CLASSES, JournalNote, Note, NoteType, type_fields
from app.models.tag import Tag
from app.repositories.base import Repository
from app.services.errors import ServiceError

_SHARED_UPDATABLE_FIELDS = frozenset({"body", "collection_id", "tag_ids"})


class NoteError(ServiceError):
    """Base class for note rule violations."""


class NoteNotFoundError(NoteError):
    code = "note_not_found"
    message = "Note not found"


class NoteCollectionNotFoundError(NoteError):
    code = "collection_not_found"
    message = "Collection not found"


class NoteTagNotFoundError(NoteError):
    code = "tag_not_found"
    message = "Tag not found"


class DuplicateTagIdError(NoteError):
    code = "duplicate_tag_id"
    message = "Duplicate tag id"


class NoteTypeChangeError(NoteError):
    code = "note_type_change"
    message = "Note type cannot be changed"


class EmptyNoteUpdateError(NoteError):
    code = "empty_update"
    message = "At least one field must be provided"


class FieldNotAllowedError(NoteError):
    code = "field_not_allowed"
    message = "Field not allowed for this note type"


class PromptLockedError(NoteError):
    code = "prompt_locked"
    message = "Prompt cannot be changed once set"


class PeriodRequiresRetrospectiveError(NoteError):
    code = "period_requires_retrospective"
    message = "Period requires is_retrospective"


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
        created_at = self._clock()
        if note_type == "journal" and fields.get("entry_date") is None:
            fields["entry_date"] = created_at
        note = NOTE_CLASSES[note_type](
            id=self._id_factory(),
            body=body,
            collection_id=collection_id,
            tag_ids=list(tag_ids),
            created_at=created_at,
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
        if isinstance(note, JournalNote):
            self._check_journal_update(note, updates)
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

    @staticmethod
    def _check_journal_update(note: JournalNote, updates: Mapping[str, Any]) -> None:
        """A prompt can be set once; the resulting note may only have a period if it is a retrospective."""
        if "prompt" in updates and note.prompt is not None and updates["prompt"] != note.prompt:
            raise PromptLockedError()
        is_retrospective = updates.get("is_retrospective", note.is_retrospective)
        period = updates.get("period", note.period)
        if period is not None and not is_retrospective:
            raise PeriodRequiresRetrospectiveError()

    def _check_tags(self, tag_ids: Sequence[str]) -> None:
        if len(set(tag_ids)) != len(tag_ids):
            raise DuplicateTagIdError()
        for tag_id in tag_ids:
            if self._tags.get(tag_id) is None:
                raise NoteTagNotFoundError()

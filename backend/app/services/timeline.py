"""The unified timeline: notes of every Type, newest first, one cursor page at a time."""

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from datetime import datetime

from app.models.collection import Collection
from app.models.note import Note, NoteType
from app.models.tag import Tag
from app.repositories.base import Repository
from app.services.errors import ServiceError

_CHECKSUM_LENGTH = 16


class TimelineError(ServiceError):
    """Base class for timeline request errors."""


class InvalidCursorError(TimelineError):
    code = "invalid_cursor"
    message = "Invalid cursor"


class TimelineCollectionNotFoundError(TimelineError):
    code = "collection_not_found"
    message = "Collection not found"


class TimelineTagNotFoundError(TimelineError):
    code = "tag_not_found"
    message = "Tag not found"


class DescendantsWithoutCollectionError(TimelineError):
    code = "descendants_require_collection"
    message = "include_descendants requires collection_id"


class UntaggedWithTagError(TimelineError):
    code = "untagged_with_tag"
    message = "untagged cannot be combined with tag_id"


@dataclass(frozen=True)
class TimelineFilters:
    collection_id: str | None = None
    include_descendants: bool = False
    type: NoteType | None = None
    tag_id: str | None = None
    untagged: bool = False

    def fingerprint(self) -> str:
        canonical = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:_CHECKSUM_LENGTH]


@dataclass(frozen=True)
class TimelinePage:
    items: list[Note]
    next_cursor: str | None


type _SortKey = tuple[datetime, str]


def _sort_key(note: Note) -> _SortKey:
    return note.created_at, note.id


def _signature(key: bytes, text: str) -> str:
    return hmac.new(key, text.encode(), hashlib.sha256).hexdigest()[:_CHECKSUM_LENGTH]


def encode_cursor(position: _SortKey, filters: TimelineFilters, key: bytes) -> str:
    """An opaque token: the last item's sort key plus the filters it belongs to, signed with `key`."""
    created_at, note_id = position
    body = json.dumps(
        {"t": created_at.isoformat(), "i": note_id, "f": filters.fingerprint()},
        sort_keys=True,
        separators=(",", ":"),
    )
    token = _signature(key, body) + body
    return base64.urlsafe_b64encode(token.encode()).decode().rstrip("=")


def decode_cursor(cursor: str, filters: TimelineFilters, key: bytes) -> _SortKey:
    try:
        token = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        signature, body = token[:_CHECKSUM_LENGTH], token[_CHECKSUM_LENGTH:]
        if not hmac.compare_digest(signature, _signature(key, body)):
            raise InvalidCursorError()
        data = json.loads(body)
        if not isinstance(data, dict):
            raise InvalidCursorError()
        created_at = datetime.fromisoformat(data["t"])
        note_id = data["i"]
        fingerprint = data["f"]
    except (
        binascii.Error,
        UnicodeError,
        ValueError,
        KeyError,
        TypeError,
        RecursionError,
    ) as error:
        raise InvalidCursorError() from error
    if created_at.tzinfo is None or not isinstance(note_id, str) or fingerprint != filters.fingerprint():
        raise InvalidCursorError()
    return created_at, note_id


class TimelineService:
    def __init__(
        self,
        notes: Repository[Note],
        collections: Repository[Collection],
        tags: Repository[Tag],
        cursor_key: bytes,
    ) -> None:
        self._notes = notes
        self._collections = collections
        self._tags = tags
        self._cursor_key = cursor_key

    def page(self, filters: TimelineFilters, limit: int, cursor: str | None = None) -> TimelinePage:
        """Return up to `limit` matching notes after `cursor`, newest first (ties: higher id first)."""
        self._check_filters(filters)
        after = decode_cursor(cursor, filters, self._cursor_key) if cursor is not None else None
        collection_ids = self._collection_scope(filters)
        matching = sorted(
            (note for note in self._notes.list() if self._matches(note, filters, collection_ids)),
            key=_sort_key,
            reverse=True,
        )
        if after is not None:
            matching = [note for note in matching if _sort_key(note) < after]
        items = matching[:limit]
        has_more = len(matching) > limit
        next_cursor = (
            encode_cursor(_sort_key(items[-1]), filters, self._cursor_key) if has_more else None
        )
        return TimelinePage(items=items, next_cursor=next_cursor)

    def _check_filters(self, filters: TimelineFilters) -> None:
        if filters.include_descendants and filters.collection_id is None:
            raise DescendantsWithoutCollectionError()
        if filters.untagged and filters.tag_id is not None:
            raise UntaggedWithTagError()
        if filters.collection_id is not None and self._collections.get(filters.collection_id) is None:
            raise TimelineCollectionNotFoundError()
        if filters.tag_id is not None and self._tags.get(filters.tag_id) is None:
            raise TimelineTagNotFoundError()

    def _collection_scope(self, filters: TimelineFilters) -> set[str] | None:
        """The collection ids a note may be in, or `None` when not filtering by collection."""
        if filters.collection_id is None:
            return None
        scope = {filters.collection_id}
        if not filters.include_descendants:
            return scope
        children: dict[str, list[str]] = {}
        for collection in self._collections.list():
            if collection.parent_id is not None:
                children.setdefault(collection.parent_id, []).append(collection.id)
        pending = [filters.collection_id]
        while pending:
            for child in children.get(pending.pop(), []):
                if child not in scope:
                    scope.add(child)
                    pending.append(child)
        return scope

    @staticmethod
    def _matches(note: Note, filters: TimelineFilters, collection_ids: set[str] | None) -> bool:
        if collection_ids is not None and note.collection_id not in collection_ids:
            return False
        if filters.type is not None and note.type != filters.type:
            return False
        if filters.tag_id is not None and filters.tag_id not in note.tag_ids:
            return False
        return not (filters.untagged and note.tag_ids)

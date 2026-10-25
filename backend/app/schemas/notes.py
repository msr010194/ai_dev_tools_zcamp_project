"""Request and response models for `/notes`, as discriminated unions on `type` (one variant per Type)."""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    StringConstraints,
    TypeAdapter,
    field_validator,
    model_validator,
)

from app.models.note import Note, NoteType, ReferenceKind, RetroPeriod

MAX_BODY_LENGTH = 100_000
MAX_MOOD_LENGTH = 100
MAX_PROMPT_LENGTH = 500
MAX_MEMORY_TEXT_LENGTH = 200
MAX_LINK_LENGTH = 2048


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


def _not_null(value: Any) -> Any:
    if value is None:
        raise ValueError("may not be null")
    return value


def _require_str(value: Any) -> Any:
    """Reject numbers etc. that Pydantic would otherwise coerce into dates."""
    if not isinstance(value, str):
        raise ValueError("must be a string")
    return value


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _http_url(value: str) -> str:
    """Loose check: an http(s) scheme, a host and no whitespace. The link is kept exactly as sent."""
    if any(char.isspace() for char in value):
        raise ValueError("must not contain whitespace")
    try:
        parts = urlsplit(value)
        host = parts.hostname
    except ValueError as error:
        raise ValueError("must be a valid URL") from error
    if parts.scheme.lower() not in ("http", "https") or not host:
        raise ValueError("must be an absolute http or https URL with a host")
    return value


def _text(max_length: int) -> StringConstraints:
    return StringConstraints(min_length=1, max_length=max_length, strict=True)


# Free text is stored exactly as sent (not trimmed) but must contain more than whitespace.
NoteBody = Annotated[str, _text(MAX_BODY_LENGTH), AfterValidator(_not_blank)]
Mood = Annotated[str, _text(MAX_MOOD_LENGTH), AfterValidator(_not_blank)]
Prompt = Annotated[str, _text(MAX_PROMPT_LENGTH), AfterValidator(_not_blank)]
MemoryText = Annotated[str, _text(MAX_MEMORY_TEXT_LENGTH), AfterValidator(_not_blank)]
Link = Annotated[str, _text(MAX_LINK_LENGTH), AfterValidator(_http_url)]
CollectionId = Annotated[str, StringConstraints(min_length=1, strict=True)]
TagId = StrictStr
# An ISO 8601 string with a timezone offset, normalised to UTC.
UtcDatetime = Annotated[AwareDatetime, BeforeValidator(_require_str), AfterValidator(_to_utc)]

SHARED_CREATE_FIELDS = frozenset({"type", "body", "collection_id", "tag_ids"})


class NoteCreateBase(BaseModel):
    """Fields every Type accepts on create; each variant narrows `type` and forbids anything else."""

    model_config = ConfigDict(extra="forbid")

    type: NoteType
    body: NoteBody
    collection_id: CollectionId
    tag_ids: list[TagId] = Field(default_factory=list)


class JournalNoteCreate(NoteCreateBase):
    type: Literal["journal"]
    entry_date: UtcDatetime | None = None
    mood: Mood | None = None
    prompt: Prompt | None = None
    is_retrospective: StrictBool | None = None
    period: RetroPeriod | None = None

    @field_validator("entry_date", "is_retrospective", mode="before")
    @classmethod
    def _required_not_null(cls, value: Any) -> Any:
        return _not_null(value)

    @model_validator(mode="after")
    def _period_needs_retrospective(self) -> Self:
        if self.period is not None and not self.is_retrospective:
            raise ValueError("Period requires is_retrospective")
        return self


class IdeaNoteCreate(NoteCreateBase):
    type: Literal["idea"]


class ReferenceNoteCreate(NoteCreateBase):
    type: Literal["reference"]
    sub_kind: ReferenceKind | None = None
    link: Link | None = None

    @field_validator("sub_kind", mode="before")
    @classmethod
    def _required_not_null(cls, value: Any) -> Any:
        return _not_null(value)


class PlanNoteCreate(NoteCreateBase):
    type: Literal["plan"]


class MemoryNoteCreate(NoteCreateBase):
    type: Literal["memory"]
    when: MemoryText | None = None
    where: MemoryText | None = None


NoteCreate = Annotated[
    JournalNoteCreate | IdeaNoteCreate | ReferenceNoteCreate | PlanNoteCreate | MemoryNoteCreate,
    Field(discriminator="type"),
]


class NoteUpdate(BaseModel):
    """Partial update; omitted fields keep their value.

    Explicit `null` is rejected for shared and required fields, and clears optional Type fields.
    Type fields are listed for every Type here; the service rejects those that don't belong to the note.
    """

    model_config = ConfigDict(extra="forbid")

    type: NoteType | None = None
    body: NoteBody | None = None
    collection_id: CollectionId | None = None
    tag_ids: list[TagId] | None = None
    entry_date: UtcDatetime | None = None
    mood: Mood | None = None
    prompt: Prompt | None = None
    is_retrospective: StrictBool | None = None
    period: RetroPeriod | None = None
    sub_kind: ReferenceKind | None = None
    link: Link | None = None
    when: MemoryText | None = None
    where: MemoryText | None = None

    @field_validator(
        "type",
        "body",
        "collection_id",
        "tag_ids",
        "entry_date",
        "is_retrospective",
        "sub_kind",
        mode="before",
    )
    @classmethod
    def _required_not_null(cls, value: Any) -> Any:
        return _not_null(value)


class NoteOutBase(BaseModel):
    """Fields every Type returns; each variant narrows `type`."""

    id: str
    type: NoteType
    body: str
    collection_id: str
    tag_ids: list[str]
    created_at: datetime
    last_resurfaced_at: datetime | None
    resurface_count: int


class JournalNoteOut(NoteOutBase):
    type: Literal["journal"]
    entry_date: datetime
    mood: str | None
    prompt: str | None
    is_retrospective: bool
    period: RetroPeriod | None


class IdeaNoteOut(NoteOutBase):
    type: Literal["idea"]


class ReferenceNoteOut(NoteOutBase):
    type: Literal["reference"]
    sub_kind: ReferenceKind
    link: str | None


class PlanNoteOut(NoteOutBase):
    type: Literal["plan"]


class MemoryNoteOut(NoteOutBase):
    type: Literal["memory"]
    when: str | None
    where: str | None


NoteOut = Annotated[
    JournalNoteOut | IdeaNoteOut | ReferenceNoteOut | PlanNoteOut | MemoryNoteOut,
    Field(discriminator="type"),
]

_note_out_adapter: TypeAdapter[Any] = TypeAdapter(NoteOut)


def to_note_out(note: Note) -> NoteOutBase:
    return _note_out_adapter.validate_python(note.model_dump())

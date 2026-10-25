"""Request and response models for `/notes`, as discriminated unions on `type` (one variant per Type)."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    StringConstraints,
    TypeAdapter,
    field_validator,
)

from app.models.note import Note, NoteType

MAX_BODY_LENGTH = 100_000
MAX_MEMORY_TEXT_LENGTH = 200


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


def _not_null(value: Any) -> Any:
    if value is None:
        raise ValueError("may not be null")
    return value


def _text(max_length: int) -> StringConstraints:
    return StringConstraints(min_length=1, max_length=max_length, strict=True)


# Free text is stored exactly as sent (not trimmed) but must contain more than whitespace.
NoteBody = Annotated[str, _text(MAX_BODY_LENGTH), AfterValidator(_not_blank)]
MemoryText = Annotated[str, _text(MAX_MEMORY_TEXT_LENGTH), AfterValidator(_not_blank)]
CollectionId = Annotated[str, StringConstraints(min_length=1, strict=True)]
TagId = StrictStr

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


class IdeaNoteCreate(NoteCreateBase):
    type: Literal["idea"]


class ReferenceNoteCreate(NoteCreateBase):
    type: Literal["reference"]


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
    when: MemoryText | None = None
    where: MemoryText | None = None

    @field_validator("type", "body", "collection_id", "tag_ids", mode="before")
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


class IdeaNoteOut(NoteOutBase):
    type: Literal["idea"]


class ReferenceNoteOut(NoteOutBase):
    type: Literal["reference"]


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

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


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("body must not be blank")
    return value


# Not trimmed: the body is stored exactly as sent, but it must contain something other than whitespace.
NoteBody = Annotated[
    str,
    StringConstraints(min_length=1, max_length=MAX_BODY_LENGTH, strict=True),
    AfterValidator(_not_blank),
]
CollectionId = Annotated[str, StringConstraints(min_length=1, strict=True)]
TagId = StrictStr


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


NoteCreate = Annotated[
    JournalNoteCreate | IdeaNoteCreate | ReferenceNoteCreate | PlanNoteCreate | MemoryNoteCreate,
    Field(discriminator="type"),
]


class NoteUpdate(BaseModel):
    """Partial update; omitted fields keep their value, explicit `null` is rejected."""

    model_config = ConfigDict(extra="forbid")

    type: NoteType | None = None
    body: NoteBody | None = None
    collection_id: CollectionId | None = None
    tag_ids: list[TagId] | None = None

    @field_validator("type", "body", "collection_id", "tag_ids", mode="before")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("may not be null")
        return value


class NoteOutBase(BaseModel):
    """Fields every Type returns; each variant narrows `type`."""

    id: str
    type: NoteType
    body: str
    collection_id: str
    tag_ids: list[str]
    created_at: datetime


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


NoteOut = Annotated[
    JournalNoteOut | IdeaNoteOut | ReferenceNoteOut | PlanNoteOut | MemoryNoteOut,
    Field(discriminator="type"),
]

_note_out_adapter: TypeAdapter[Any] = TypeAdapter(NoteOut)


def to_note_out(note: Note) -> NoteOutBase:
    return _note_out_adapter.validate_python(note.model_dump())

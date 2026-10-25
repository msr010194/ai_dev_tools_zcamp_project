"""Note entities: the shared `Note` fields plus one subclass per Type that adds that Type's own fields."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

NoteType = Literal["journal", "idea", "reference", "plan", "memory"]


class Note(BaseModel):
    id: str
    type: NoteType
    body: str
    collection_id: str
    tag_ids: list[str]
    created_at: datetime
    last_resurfaced_at: datetime | None = None
    resurface_count: int = 0


class JournalNote(Note):
    type: Literal["journal"] = "journal"


class IdeaNote(Note):
    type: Literal["idea"] = "idea"


class ReferenceNote(Note):
    type: Literal["reference"] = "reference"


class PlanNote(Note):
    type: Literal["plan"] = "plan"


class MemoryNote(Note):
    type: Literal["memory"] = "memory"
    when: str | None = None
    where: str | None = None


NOTE_CLASSES: dict[str, type[Note]] = {
    "journal": JournalNote,
    "idea": IdeaNote,
    "reference": ReferenceNote,
    "plan": PlanNote,
    "memory": MemoryNote,
}


def type_fields(note_type: str) -> frozenset[str]:
    """The fields only notes of `note_type` have."""
    return frozenset(NOTE_CLASSES[note_type].model_fields) - frozenset(Note.model_fields)

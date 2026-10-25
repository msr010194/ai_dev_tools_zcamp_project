"""Note entities: the shared `Note` fields plus one subclass per Type that adds that Type's own fields."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

NoteType = Literal["journal", "idea", "reference", "plan", "memory"]
RetroPeriod = Literal["weekly", "monthly"]
ReferenceKind = Literal["written", "visual", "audio"]
PlanState = Literal["not_started", "in_progress", "done", "abandoned"]


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
    entry_date: datetime
    mood: str | None = None
    prompt: str | None = None
    is_retrospective: bool = False
    period: RetroPeriod | None = None


class IdeaNote(Note):
    type: Literal["idea"] = "idea"


class ReferenceNote(Note):
    type: Literal["reference"] = "reference"
    sub_kind: ReferenceKind = "written"
    link: str | None = None


class ChecklistItem(BaseModel):
    """One Plan checklist item; its position is its index in the plan's `checklist`."""

    text: str
    done: bool = False


class PlanNote(Note):
    type: Literal["plan"] = "plan"
    target_date: date | None = None
    state: PlanState = "not_started"
    checklist: list[ChecklistItem] = Field(default_factory=list)


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

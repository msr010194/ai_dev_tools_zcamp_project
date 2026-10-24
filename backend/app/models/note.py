"""The `Note` entity: one piece of writing of a given Type, filed in exactly one collection."""

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

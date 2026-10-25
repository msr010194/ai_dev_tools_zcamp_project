"""Response model for `GET /timeline`."""

from pydantic import BaseModel

from app.schemas.notes import NoteOut


class TimelinePageOut(BaseModel):
    items: list[NoteOut]
    next_cursor: str | None

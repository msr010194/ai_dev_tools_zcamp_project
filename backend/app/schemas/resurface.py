"""Response model for `GET /resurface`."""

from pydantic import BaseModel

from app.schemas.notes import NoteOut


class ResurfaceOut(BaseModel):
    items: list[NoteOut]

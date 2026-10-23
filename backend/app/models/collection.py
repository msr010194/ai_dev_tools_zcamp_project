"""The `Collection` entity: a named node in the collection tree."""

from pydantic import BaseModel


class Collection(BaseModel):
    id: str
    name: str
    parent_id: str | None = None

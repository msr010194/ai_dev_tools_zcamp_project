"""The `Tag` entity: a curated label that is only created on purpose via `POST /tags`."""

from pydantic import BaseModel


class Tag(BaseModel):
    id: str
    name: str

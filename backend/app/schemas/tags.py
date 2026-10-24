"""Request and response models for the Tags API."""

from pydantic import BaseModel, ConfigDict

from app.schemas.collections import CollectionName

# Tag names follow exactly the same rules (trimming, non-empty, length limit) as collection names.
TagName = CollectionName


class TagCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: TagName


class TagUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: TagName


class TagOut(BaseModel):
    id: str
    name: str

"""Request and response models for the Collections API."""

from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

CollectionName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, strict=True)
]


class CollectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CollectionName
    parent_id: str | None = None


class CollectionUpdate(BaseModel):
    """Rename and/or move; an omitted `parent_id` means "don't move", `null` means top level."""

    model_config = ConfigDict(extra="forbid")

    name: CollectionName | None = None
    parent_id: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _name_not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("name may not be null")
        return value

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one of 'name' or 'parent_id'")
        return self

    @property
    def moves(self) -> bool:
        return "parent_id" in self.model_fields_set


class CollectionOut(BaseModel):
    id: str
    name: str
    parent_id: str | None


class CollectionTreeNode(BaseModel):
    id: str
    name: str
    parent_id: str | None
    children: list["CollectionTreeNode"]

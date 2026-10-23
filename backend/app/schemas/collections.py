"""Request and response models for the Collections API."""

import json
from collections.abc import Iterator
from typing import Annotated, Any, Self, TypedDict

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
    """Documents the `GET /collections` node shape in OpenAPI.

    The endpoint itself returns `CollectionTree` dicts encoded by `dump_tree_json`, because
    Pydantic's recursive serializer fails on deep (about 99+ levels) trees.
    """

    id: str
    name: str
    parent_id: str | None
    children: list["CollectionTreeNode"]


class CollectionTree(TypedDict):
    """Plain-dict tree node with the same fields as `CollectionTreeNode`."""

    id: str
    name: str
    parent_id: str | None
    children: list["CollectionTree"]


def dump_tree_json(roots: list[CollectionTree]) -> str:
    """Encode a tree as compact JSON without recursion, so any depth works."""
    parts = ["["]
    pending: list[Iterator[CollectionTree]] = [iter(roots)]
    needs_comma = [False]
    while pending:
        node = next(pending[-1], None)
        if node is None:
            pending.pop()
            needs_comma.pop()
            parts.append("]}" if pending else "]")
            continue
        if needs_comma[-1]:
            parts.append(",")
        needs_comma[-1] = True
        parts.append(
            f'{{"id":{_json_scalar(node["id"])},"name":{_json_scalar(node["name"])},'
            f'"parent_id":{_json_scalar(node["parent_id"])},"children":['
        )
        pending.append(iter(node["children"]))
        needs_comma.append(False)
    return "".join(parts)


def _json_scalar(value: str | None) -> str:
    return json.dumps(value, ensure_ascii=False)

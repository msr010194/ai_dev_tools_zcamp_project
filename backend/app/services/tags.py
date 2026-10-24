"""Tag use cases: the curated tag list and its create/rename rules.

`TagService.create` is the only way a tag comes into existence. Other features (such as notes)
check tag ids with `TagService.get`, which fails for unknown ids, and never create tags themselves.
"""

import uuid
from collections.abc import Callable

from app.models.tag import Tag
from app.repositories.base import Repository


class TagError(Exception):
    """Base class for tag rule violations; `str(error)` is the client-facing message."""

    message = "Tag error"

    def __init__(self) -> None:
        super().__init__(self.message)


class TagNotFoundError(TagError):
    message = "Tag not found"


class DuplicateTagNameError(TagError):
    message = "A tag with that name already exists"


def _sort_key(tag: Tag) -> tuple[str, str]:
    return tag.name.casefold(), tag.id


class TagService:
    """Expects names that are already trimmed and validated (see `app.schemas.tags`)."""

    def __init__(
        self,
        tags: Repository[Tag],
        id_factory: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self._tags = tags
        self._new_id = id_factory

    def list_tags(self) -> list[Tag]:
        return sorted(self._tags.list(), key=_sort_key)

    def get(self, tag_id: str) -> Tag:
        tag = self._tags.get(tag_id)
        if tag is None:
            raise TagNotFoundError()
        return tag

    def create(self, name: str) -> Tag:
        self._require_unique_name(name, exclude_id=None)
        return self._tags.add(Tag(id=self._new_id(), name=name))

    def rename(self, tag_id: str, name: str) -> Tag:
        tag = self.get(tag_id)
        self._require_unique_name(name, exclude_id=tag_id)
        result = self._tags.update(tag.model_copy(update={"name": name}))
        if result is None:
            raise TagNotFoundError()
        return result

    def _require_unique_name(self, name: str, exclude_id: str | None) -> None:
        folded = name.casefold()
        for other in self._tags.list():
            if other.id != exclude_id and other.name.casefold() == folded:
                raise DuplicateTagNameError()

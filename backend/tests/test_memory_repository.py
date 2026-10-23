import pytest
from pydantic import BaseModel

from app.repositories.base import Repository
from app.repositories.memory import InMemoryRepository


class Item(BaseModel):
    id: int
    name: str
    tags: list[str] = []


@pytest.fixture
def repo() -> InMemoryRepository[Item]:
    return InMemoryRepository[Item]()


def test_in_memory_repository_satisfies_the_interface():
    assert issubclass(InMemoryRepository, Repository)
    repo: Repository[Item] = InMemoryRepository[Item]()
    assert isinstance(repo, Repository)


def test_add_then_get_returns_equal_entity(repo):
    item = Item(id=1, name="first")
    repo.add(item)
    assert repo.get(1) == item


def test_list_returns_all_added_entities(repo):
    items = [Item(id=1, name="a"), Item(id=2, name="b"), Item(id=3, name="c")]
    for item in items:
        repo.add(item)
    assert sorted(repo.list(), key=lambda i: i.id) == items


def test_list_is_empty_for_new_repository(repo):
    assert repo.list() == []


def test_get_unknown_id_returns_none(repo):
    assert repo.get(42) is None


def test_add_duplicate_id_raises_and_keeps_stored_entity(repo):
    repo.add(Item(id=1, name="original"))
    with pytest.raises(ValueError):
        repo.add(Item(id=1, name="duplicate"))
    assert repo.get(1) == Item(id=1, name="original")
    assert len(repo.list()) == 1


def test_update_existing_replaces_entity(repo):
    repo.add(Item(id=1, name="before"))
    updated = repo.update(Item(id=1, name="after"))
    assert updated == Item(id=1, name="after")
    assert repo.get(1) == Item(id=1, name="after")
    assert len(repo.list()) == 1


def test_update_unknown_id_returns_none_and_stores_nothing(repo):
    assert repo.update(Item(id=7, name="ghost")) is None
    assert repo.get(7) is None
    assert repo.list() == []


def test_delete_existing_returns_true_and_removes(repo):
    repo.add(Item(id=1, name="doomed"))
    assert repo.delete(1) is True
    assert repo.get(1) is None
    assert repo.list() == []


def test_delete_unknown_id_returns_false(repo):
    repo.add(Item(id=1, name="kept"))
    assert repo.delete(99) is False
    assert repo.list() == [Item(id=1, name="kept")]


def test_mutating_object_passed_to_add_does_not_change_store(repo):
    item = Item(id=1, name="original", tags=["x"])
    repo.add(item)
    item.name = "mutated"
    item.tags.append("y")
    assert repo.get(1) == Item(id=1, name="original", tags=["x"])


def test_mutating_object_returned_by_add_does_not_change_store(repo):
    returned = repo.add(Item(id=1, name="original"))
    returned.name = "mutated"
    assert repo.get(1) == Item(id=1, name="original")


def test_mutating_object_returned_by_get_does_not_change_store(repo):
    repo.add(Item(id=1, name="original", tags=["x"]))
    fetched = repo.get(1)
    fetched.name = "mutated"
    fetched.tags.append("y")
    assert repo.get(1) == Item(id=1, name="original", tags=["x"])


def test_mutating_object_returned_by_list_does_not_change_store(repo):
    repo.add(Item(id=1, name="original", tags=["x"]))
    listed = repo.list()
    listed[0].name = "mutated"
    listed[0].tags.append("y")
    listed.clear()
    assert repo.list() == [Item(id=1, name="original", tags=["x"])]


def test_mutation_is_stored_once_update_is_called(repo):
    repo.add(Item(id=1, name="original"))
    fetched = repo.get(1)
    fetched.name = "changed"
    assert repo.get(1).name == "original"
    repo.update(fetched)
    assert repo.get(1).name == "changed"
    fetched.name = "changed again"
    assert repo.get(1).name == "changed"


def test_separate_instances_do_not_share_data():
    first = InMemoryRepository[Item]()
    second = InMemoryRepository[Item]()
    first.add(Item(id=1, name="only in first"))
    assert second.get(1) is None
    assert second.list() == []
    second.add(Item(id=1, name="only in second"))
    assert first.get(1) == Item(id=1, name="only in first")

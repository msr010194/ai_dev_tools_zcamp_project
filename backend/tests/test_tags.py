"""Tests for the Tags API and TagService (#9)."""

import uuid
from pathlib import Path
from typing import get_args

import pytest

from app.models.tag import Tag
from app.repositories.memory import InMemoryRepository
from app.schemas.collections import CollectionName
from app.schemas.tags import TagName
from app.services.tags import DuplicateTagNameError, TagNotFoundError, TagService

DUPLICATE = "A tag with that name already exists"
NOT_FOUND = "Tag not found"
MAX_NAME = next(
    meta.max_length
    for meta in get_args(CollectionName)[1:]
    if getattr(meta, "max_length", None) is not None
)
APP_DIR = Path(__file__).resolve().parents[1] / "app"


def create(client, name):
    response = client.post("/tags", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def list_tags(client):
    response = client.get("/tags")
    assert response.status_code == 200, response.text
    return response.json()


def names(client):
    return [tag["name"] for tag in list_tags(client)]


def make_service(*tags, id_factory=None):
    repo: InMemoryRepository[Tag] = InMemoryRepository()
    for tag in tags:
        repo.add(tag)
    return TagService(repo) if id_factory is None else TagService(repo, id_factory=id_factory)


# Store wiring


def test_store_has_an_empty_tag_repository(store):
    assert isinstance(store.tags, InMemoryRepository)
    assert store.tags.list() == []


def test_tag_name_reuses_the_collection_name_limit():
    assert TagName is CollectionName


# List


def test_list_is_empty_without_tags(client):
    response = client.get("/tags")
    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_id_and_name_objects(client):
    created = create(client, "Work")
    assert list_tags(client) == [{"id": created["id"], "name": "Work"}]


def test_list_is_sorted_by_casefolded_name(client):
    for name in ["beta", "Alpha", "gamma"]:
        create(client, name)
    assert names(client) == ["Alpha", "beta", "gamma"]


def test_list_sorts_casefold_equal_names_by_id(client, store):
    store.tags.add(Tag(id="b", name="SAME"))
    store.tags.add(Tag(id="c", name="Same"))
    store.tags.add(Tag(id="a", name="same"))
    expected = [
        {"id": "a", "name": "same"},
        {"id": "b", "name": "SAME"},
        {"id": "c", "name": "Same"},
    ]
    assert list_tags(client) == expected
    assert list_tags(client) == expected


def test_list_order_does_not_depend_on_insertion_order():
    tags = [
        Tag(id="2", name="same"),
        Tag(id="1", name="Same"),
        Tag(id="3", name="alpha"),
        Tag(id="0", name="Beta"),
    ]
    forward = [tag.id for tag in make_service(*tags).list_tags()]
    backward = [tag.id for tag in make_service(*reversed(tags)).list_tags()]
    assert forward == backward == ["3", "0", "1", "2"]


# Create


def test_create_trims_name_and_returns_201(client):
    response = client.post("/tags", json={"name": "  Work  "})
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "name"}
    assert isinstance(body["id"], str) and body["id"]
    assert body["name"] == "Work"
    assert list_tags(client) == [body]


def test_create_keeps_inner_whitespace(client):
    assert create(client, " \tDeep   Work \n")["name"] == "Deep   Work"


def test_create_assigns_distinct_ids(client):
    first = create(client, "One")
    second = create(client, "Two")
    assert first["id"] != second["id"]


DUPLICATE_PAIRS = [
    pytest.param("Work", "Work", id="exact"),
    pytest.param("Work", "work", id="lower"),
    pytest.param("Work", "WORK", id="upper"),
    pytest.param("Work", " Work ", id="surrounding-whitespace"),
    pytest.param("work", "\tWORK \n", id="case-and-whitespace"),
    pytest.param("Straße", "STRASSE", id="casefold-sharp-s"),
    pytest.param("STRASSE", "straße", id="casefold-sharp-s-reverse"),
]


@pytest.mark.parametrize(("existing", "candidate"), DUPLICATE_PAIRS)
def test_create_duplicate_name_returns_409(client, existing, candidate):
    create(client, existing)
    before = list_tags(client)
    response = client.post("/tags", json={"name": candidate})
    assert response.status_code == 409
    assert response.json() == {"detail": DUPLICATE}
    assert list_tags(client) == before


# Rename


def test_rename_returns_updated_tag_and_keeps_id(client):
    tag = create(client, "Work")
    response = client.patch(f"/tags/{tag['id']}", json={"name": "Projects"})
    assert response.status_code == 200
    assert response.json() == {"id": tag["id"], "name": "Projects"}
    assert list_tags(client) == [{"id": tag["id"], "name": "Projects"}]


def test_rename_trims_and_moves_tag_to_new_sorted_position(client):
    alpha = create(client, "Alpha")
    create(client, "Beta")
    create(client, "Gamma")
    response = client.patch(f"/tags/{alpha['id']}", json={"name": "  Delta  "})
    assert response.status_code == 200
    assert response.json() == {"id": alpha["id"], "name": "Delta"}
    listed = list_tags(client)
    assert [tag["name"] for tag in listed] == ["Beta", "Delta", "Gamma"]
    assert listed[1]["id"] == alpha["id"]


@pytest.mark.parametrize(("existing", "candidate"), DUPLICATE_PAIRS)
def test_rename_to_name_of_other_tag_returns_409(client, existing, candidate):
    create(client, existing)
    other = create(client, "Home")
    before = list_tags(client)
    response = client.patch(f"/tags/{other['id']}", json={"name": candidate})
    assert response.status_code == 409
    assert response.json() == {"detail": DUPLICATE}
    assert list_tags(client) == before


@pytest.mark.parametrize(
    ("current", "new", "stored"),
    [
        pytest.param("work", "work", "work", id="same"),
        pytest.param("work", "Work", "Work", id="different-case"),
        pytest.param("Work", "  WORK  ", "WORK", id="different-case-padded"),
        pytest.param("Straße", "STRASSE", "STRASSE", id="casefold-sharp-s"),
    ],
)
def test_rename_to_own_name_is_allowed(client, current, new, stored):
    tag = create(client, current)
    response = client.patch(f"/tags/{tag['id']}", json={"name": new})
    assert response.status_code == 200
    assert response.json() == {"id": tag["id"], "name": stored}
    assert list_tags(client) == [{"id": tag["id"], "name": stored}]


@pytest.mark.parametrize("missing_id", ["does-not-exist", str(uuid.uuid4())])
def test_rename_unknown_id_returns_404(client, missing_id):
    create(client, "Work")
    before = list_tags(client)
    response = client.patch(f"/tags/{missing_id}", json={"name": "Projects"})
    assert response.status_code == 404
    assert response.json() == {"detail": NOT_FOUND}
    assert list_tags(client) == before


# Validation

INVALID_BODIES = [
    pytest.param({}, id="missing"),
    pytest.param({"name": None}, id="null"),
    pytest.param({"name": 123}, id="number"),
    pytest.param({"name": True}, id="bool"),
    pytest.param({"name": ["x"]}, id="list"),
    pytest.param({"name": ""}, id="empty"),
    pytest.param({"name": "   "}, id="spaces"),
    pytest.param({"name": " \t\n "}, id="mixed-whitespace"),
    pytest.param({"name": "x" * (MAX_NAME + 1)}, id="too-long"),
    pytest.param({"name": "  " + "x" * (MAX_NAME + 1) + "  "}, id="too-long-padded"),
    pytest.param({"name": "x", "id": 5}, id="extra-id"),
    pytest.param({"name": "x", "color": "red"}, id="extra-color"),
]


def assert_validation_error(response):
    assert response.status_code == 422, response.text
    body = response.json()
    assert set(body) == {"detail"}
    assert isinstance(body["detail"], list) and body["detail"]
    for item in body["detail"]:
        assert {"loc", "msg", "type"} <= set(item)


@pytest.mark.parametrize("body", INVALID_BODIES)
def test_create_rejects_invalid_body_with_422(client, body):
    create(client, "Existing")
    before = list_tags(client)
    assert_validation_error(client.post("/tags", json=body))
    assert list_tags(client) == before


@pytest.mark.parametrize("body", INVALID_BODIES)
def test_rename_rejects_invalid_body_with_422(client, body):
    tag = create(client, "Existing")
    before = list_tags(client)
    assert_validation_error(client.patch(f"/tags/{tag['id']}", json=body))
    assert list_tags(client) == before


@pytest.mark.parametrize(
    ("raw", "stored"),
    [
        pytest.param("x" * MAX_NAME, "x" * MAX_NAME, id="exact"),
        pytest.param("  " + "y" * MAX_NAME + "\t ", "y" * MAX_NAME, id="padded"),
    ],
)
def test_create_accepts_name_at_limit(client, raw, stored):
    assert create(client, raw)["name"] == stored
    assert names(client) == [stored]


@pytest.mark.parametrize(
    ("raw", "stored"),
    [
        pytest.param("x" * MAX_NAME, "x" * MAX_NAME, id="exact"),
        pytest.param("  " + "y" * MAX_NAME + "\t ", "y" * MAX_NAME, id="padded"),
    ],
)
def test_rename_accepts_name_at_limit(client, raw, stored):
    tag = create(client, "Short")
    response = client.patch(f"/tags/{tag['id']}", json={"name": raw})
    assert response.status_code == 200
    assert response.json() == {"id": tag["id"], "name": stored}


# Error bodies match the Collections API


def _shape(response):
    body = response.json()
    detail = body["detail"]
    if isinstance(detail, list):
        return sorted(body), "list", all({"loc", "msg", "type"} <= set(item) for item in detail)
    return sorted(body), type(detail).__name__


def test_error_bodies_match_collections_api(client):
    collection = client.post("/collections", json={"name": "Shared"})
    assert collection.status_code == 201
    tag = create(client, "Shared")

    pairs = {
        404: (
            client.patch("/collections/missing", json={"name": "x"}),
            client.patch("/tags/missing", json={"name": "x"}),
        ),
        409: (
            client.post("/collections", json={"name": "shared"}),
            client.post("/tags", json={"name": "shared"}),
        ),
        422: (
            client.post("/collections", json={"name": ""}),
            client.patch(f"/tags/{tag['id']}", json={"name": ""}),
        ),
    }
    for status_code, (collections_response, tags_response) in pairs.items():
        assert collections_response.status_code == status_code
        assert tags_response.status_code == status_code
        assert _shape(tags_response) == _shape(collections_response)


# No implicit creation


def test_renames_do_not_change_tag_count(client):
    first = create(client, "One")
    create(client, "Two")
    for new_name in ["Uno", "uno", "Three"]:
        assert client.patch(f"/tags/{first['id']}", json={"name": new_name}).status_code == 200
        assert len(list_tags(client)) == 2


def test_collections_api_calls_do_not_create_tags(client):
    create(client, "Existing")
    parent = client.post("/collections", json={"name": "Work"})
    assert parent.status_code == 201
    parent_id = parent.json()["id"]
    client.post("/collections", json={"name": "Child", "parent_id": parent_id})
    client.post("/collections", json={"name": "work"})
    client.patch(f"/collections/{parent_id}", json={"name": "Projects"})
    client.patch("/collections/missing", json={"name": "Nope"})
    client.get("/collections")
    assert names(client) == ["Existing"]


def test_service_get_returns_tag_by_id():
    service = make_service(Tag(id="t1", name="Work"))
    assert service.get("t1") == Tag(id="t1", name="Work")


def test_service_get_unknown_id_raises():
    service = make_service(Tag(id="t1", name="Work"))
    with pytest.raises(TagNotFoundError):
        service.get("missing")


def test_service_get_finds_tags_created_through_api(client, store):
    tag = create(client, "Work")
    assert TagService(store.tags).get(tag["id"]) == Tag(id=tag["id"], name="Work")


def test_service_create_rejects_duplicate_instead_of_returning_existing():
    service = make_service(Tag(id="t1", name="Work"), id_factory=lambda: "t2")
    with pytest.raises(DuplicateTagNameError):
        service.create("WORK")
    assert [tag.id for tag in service.list_tags()] == ["t1"]


def test_service_has_no_get_or_create_function():
    creating = [name for name in dir(TagService) if "create" in name.lower() or "ensure" in name.lower()]
    assert creating == ["create"]


def test_app_has_no_get_or_create_function():
    offenders = [
        str(path)
        for path in APP_DIR.rglob("*.py")
        if "or_create" in path.read_text(encoding="utf-8").lower()
    ]
    assert offenders == []

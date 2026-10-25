"""Tests for the notes API (#10): CRUD for all five Types using the shared fields only."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, get_args

import pytest

from app.models.note import Note
from app.repositories.memory import InMemoryRepository
from app.schemas.notes import NoteCreate, NoteCreateBase, NoteOut, NoteOutBase

TYPES = ["journal", "idea", "reference", "plan", "memory"]
FIELDS = {
    "id",
    "type",
    "body",
    "collection_id",
    "tag_ids",
    "created_at",
    "last_resurfaced_at",
    "resurface_count",
}
OWN_FIELDS: dict[str, set[str]] = {
    "journal": {"entry_date", "mood", "prompt", "is_retrospective", "period"},
    "idea": set(),
    "reference": {"sub_kind", "link"},
    "plan": set(),
    "memory": {"when", "where"},
}
TYPE_SPECIFIC_FIELDS = {
    "mood": "happy",
    "link": "https://example.com",
    "target_date": "2026-01-01",
    "where": "Lisbon",
}
FIELD_OWNER = {"mood": "journal", "link": "reference", "target_date": "plan", "where": "memory"}
WRONG_TYPE_FIELDS = [
    (type_, field) for type_ in TYPES for field in TYPE_SPECIFIC_FIELDS if FIELD_OWNER[field] != type_
]
MISSING = object()


def make_collection(client, name: str = "Inbox", parent_id: str | None = None) -> str:
    payload: dict[str, Any] = {"name": name}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    response = client.post("/collections", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def make_tag(client, name: str) -> str:
    response = client.post("/tags", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def note_payload(collection_id: str, type_: str = "journal", body: str = "Hello", **extra: Any) -> dict:
    return {"type": type_, "body": body, "collection_id": collection_id, **extra}


def with_field(payload: dict, field: str, value: Any) -> dict:
    payload = dict(payload)
    if value is MISSING:
        payload.pop(field, None)
    else:
        payload[field] = value
    return payload


def create_note(client, collection_id: str, type_: str = "journal", **extra: Any) -> dict:
    response = client.post("/notes", json=note_payload(collection_id, type_, **extra))
    assert response.status_code == 201, response.text
    return response.json()


def get_note(client, note_id: str) -> dict:
    response = client.get(f"/notes/{note_id}")
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def inbox(client) -> str:
    return make_collection(client, "Inbox")


# --- Create -------------------------------------------------------------------------------------


@pytest.mark.parametrize("type_", TYPES)
def test_create_returns_201_with_exactly_the_shared_and_own_fields(client, inbox, type_):
    tag = make_tag(client, "work")
    response = client.post(
        "/notes", json={"type": type_, "body": "Hello", "collection_id": inbox, "tag_ids": [tag]}
    )
    assert response.status_code == 201, response.text
    note = response.json()
    assert set(note) == FIELDS | OWN_FIELDS[type_]
    assert note["type"] == type_
    assert note["body"] == "Hello"
    assert note["collection_id"] == inbox
    assert note["tag_ids"] == [tag]


def test_id_is_server_made_uuid4_and_unique(client, inbox):
    first = create_note(client, inbox)
    second = create_note(client, inbox)
    for note in (first, second):
        parsed = uuid.UUID(note["id"])
        assert parsed.version == 4
        assert str(parsed) == note["id"]
    assert first["id"] != second["id"]


def test_created_at_is_utc_server_time(client, inbox):
    before = datetime.now(UTC)
    note = create_note(client, inbox)
    after = datetime.now(UTC)
    assert isinstance(note["created_at"], str)
    created = datetime.fromisoformat(note["created_at"])
    assert created.tzinfo is not None
    assert created.utcoffset() == timedelta(0)
    assert before <= created <= after


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", str(uuid.uuid4())), ("created_at", "2026-01-01T00:00:00Z")],
)
def test_create_rejects_server_fields(client, inbox, field, value):
    response = client.post("/notes", json=note_payload(inbox, **{field: value}))
    assert response.status_code == 422


@pytest.mark.parametrize(
    "value",
    [pytest.param(MISSING, id="missing"), None, "task", "Journal", "JOURNAL", 1],
)
def test_create_rejects_bad_type(client, inbox, value):
    response = client.post("/notes", json=with_field(note_payload(inbox), "type", value))
    assert response.status_code == 422


@pytest.mark.parametrize(("type_", "field"), WRONG_TYPE_FIELDS)
def test_create_rejects_other_types_fields(client, inbox, type_, field):
    response = client.post(
        "/notes", json=note_payload(inbox, type_, **{field: TYPE_SPECIFIC_FIELDS[field]})
    )
    assert response.status_code == 422


@pytest.mark.parametrize("type_", TYPES)
def test_create_rejects_unknown_fields(client, inbox, type_):
    response = client.post("/notes", json=note_payload(inbox, type_, colour="red"))
    assert response.status_code == 422


@pytest.mark.parametrize(
    "value",
    [pytest.param(MISSING, id="missing"), None, 123, "", "  \n", ["a"]],
)
def test_create_rejects_bad_body(client, inbox, value):
    response = client.post("/notes", json=with_field(note_payload(inbox), "body", value))
    assert response.status_code == 422


def test_body_is_stored_exactly_as_sent(client, inbox):
    body = "  \n Hello,\n  world \n\n"
    note = create_note(client, inbox, body=body)
    assert note["body"] == body
    assert get_note(client, note["id"])["body"] == body


def test_body_length_limit(client, inbox):
    assert client.post("/notes", json=note_payload(inbox, body="x" * 100_000)).status_code == 201
    assert client.post("/notes", json=note_payload(inbox, body="x" * 100_001)).status_code == 422


@pytest.mark.parametrize(
    "value",
    [pytest.param(MISSING, id="missing"), None, "", 123, ["a"], ["a", "b"]],
)
def test_create_rejects_bad_collection_id(client, inbox, value):
    response = client.post("/notes", json=with_field(note_payload(inbox), "collection_id", value))
    assert response.status_code == 422


def test_create_rejects_existing_collection_inside_a_list(client, inbox):
    response = client.post("/notes", json=with_field(note_payload(inbox), "collection_id", [inbox]))
    assert response.status_code == 422


def test_create_with_unknown_collection_returns_422(client):
    response = client.post("/notes", json=note_payload("no-such-collection"))
    assert response.status_code == 422
    assert response.json() == {"detail": "Collection not found"}


def test_create_in_nested_collection(client):
    parent = make_collection(client, "Parent")
    child = make_collection(client, "Child", parent_id=parent)
    assert create_note(client, child)["collection_id"] == child


def test_tag_ids_omitted_gives_empty_list(client, inbox):
    response = client.post("/notes", json={"type": "idea", "body": "Hi", "collection_id": inbox})
    assert response.status_code == 201
    assert response.json()["tag_ids"] == []


def test_tag_ids_empty_list(client, inbox):
    note = create_note(client, inbox, tag_ids=[])
    assert note["tag_ids"] == []
    assert get_note(client, note["id"])["tag_ids"] == []


@pytest.mark.parametrize("value", [None, "a", [1], [None], [["a"]], {"a": 1}])
def test_create_rejects_bad_tag_ids(client, inbox, value):
    response = client.post("/notes", json=note_payload(inbox, tag_ids=value))
    assert response.status_code == 422


def test_tag_order_is_kept(client, inbox):
    a = make_tag(client, "a")
    b = make_tag(client, "b")
    note = create_note(client, inbox, tag_ids=[b, a])
    assert note["tag_ids"] == [b, a]
    assert get_note(client, note["id"])["tag_ids"] == [b, a]


def test_duplicate_tag_ids_are_rejected(client, inbox):
    a = make_tag(client, "a")
    response = client.post("/notes", json=note_payload(inbox, tag_ids=[a, a]))
    assert response.status_code == 422
    assert response.json() == {"detail": "Duplicate tag id"}


def test_unknown_tag_is_rejected_and_not_created(client, inbox):
    make_tag(client, "existing")
    tags_before = client.get("/tags").json()
    response = client.post("/notes", json=note_payload(inbox, tag_ids=["new-tag"]))
    assert response.status_code == 422
    assert response.json() == {"detail": "Tag not found"}
    assert client.get("/tags").json() == tags_before


def test_one_tag_on_many_notes(client, inbox):
    tag = make_tag(client, "shared")
    assert create_note(client, inbox, tag_ids=[tag])["tag_ids"] == [tag]
    assert create_note(client, inbox, "idea", tag_ids=[tag])["tag_ids"] == [tag]


@pytest.mark.parametrize(
    "case",
    ["unknown_tag", "duplicate_tag", "blank_body", "type_specific", "server_id", "bad_type"],
)
def test_rejected_post_leaves_no_note(client, store, case):
    target = make_collection(client, "Target")
    tag = make_tag(client, "t")
    payloads = {
        "unknown_tag": note_payload(target, tag_ids=["missing"]),
        "duplicate_tag": note_payload(target, tag_ids=[tag, tag]),
        "blank_body": note_payload(target, body="  "),
        "type_specific": note_payload(target, where="Lisbon"),
        "server_id": note_payload(target, id=str(uuid.uuid4())),
        "bad_type": note_payload(target, "task"),
    }
    response = client.post("/notes", json=payloads[case])
    assert response.status_code == 422
    assert store.notes.list() == []
    assert client.delete(f"/collections/{target}").status_code == 204


# --- Read ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("type_", TYPES)
def test_get_returns_the_created_note(client, inbox, type_):
    tag = make_tag(client, "t")
    created = create_note(client, inbox, type_, body="Body\n", tag_ids=[tag])
    response = client.get(f"/notes/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_note_returns_404(client):
    response = client.get(f"/notes/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Note not found"}


# --- Update -------------------------------------------------------------------------------------


@pytest.mark.parametrize("type_", TYPES)
def test_patch_each_field_alone(client, inbox, type_):
    other = make_collection(client, "Other")
    a = make_tag(client, "a")
    b = make_tag(client, "b")
    created = create_note(client, inbox, type_, body="Original", tag_ids=[a])

    expected = {**created, "body": "Changed"}
    response = client.patch(f"/notes/{created['id']}", json={"body": "Changed"})
    assert response.status_code == 200
    assert response.json() == expected
    assert get_note(client, created["id"]) == expected

    expected = {**expected, "collection_id": other}
    response = client.patch(f"/notes/{created['id']}", json={"collection_id": other})
    assert response.status_code == 200
    assert response.json() == expected
    assert get_note(client, created["id"]) == expected

    expected = {**expected, "tag_ids": [b, a]}
    response = client.patch(f"/notes/{created['id']}", json={"tag_ids": [b, a]})
    assert response.status_code == 200
    assert response.json() == expected
    assert get_note(client, created["id"]) == expected


def test_patch_with_no_fields_returns_422(client, inbox):
    created = create_note(client, inbox)
    response = client.patch(f"/notes/{created['id']}", json={})
    assert response.status_code == 422
    assert response.json() == {"detail": "At least one field must be provided"}
    assert get_note(client, created["id"]) == created


@pytest.mark.parametrize("field", ["body", "collection_id", "tag_ids", "type"])
def test_patch_explicit_null_returns_422(client, inbox, field):
    created = create_note(client, inbox)
    response = client.patch(f"/notes/{created['id']}", json={field: None})
    assert response.status_code == 422
    assert get_note(client, created["id"]) == created


@pytest.mark.parametrize(
    "payload",
    [
        {"body": ""},
        {"body": "  \n"},
        {"body": 123},
        {"body": "x" * 100_001},
        {"collection_id": ""},
        {"collection_id": 123},
        {"collection_id": ["a"]},
        {"collection_id": ["a", "b"]},
        {"tag_ids": "a"},
        {"tag_ids": [1]},
        {"type": "task"},
        {"type": "Journal"},
        {"id": "00000000-0000-4000-8000-000000000000"},
        {"created_at": "2026-01-01T00:00:00Z"},
        {"body": "Valid", "colour": "red"},
    ],
)
def test_patch_rejects_invalid_payloads_and_changes_nothing(client, inbox, payload):
    tag = make_tag(client, "t")
    created = create_note(client, inbox, body="Original", tag_ids=[tag])
    response = client.patch(f"/notes/{created['id']}", json=payload)
    assert response.status_code == 422
    assert get_note(client, created["id"]) == created


@pytest.mark.parametrize(("type_", "field"), WRONG_TYPE_FIELDS)
def test_patch_rejects_other_types_fields(client, inbox, type_, field):
    created = create_note(client, inbox, type_)
    response = client.patch(f"/notes/{created['id']}", json={field: TYPE_SPECIFIC_FIELDS[field]})
    assert response.status_code == 422
    assert get_note(client, created["id"]) == created


def test_patch_with_list_of_existing_collection_returns_422(client, inbox):
    other = make_collection(client, "Other")
    created = create_note(client, inbox)
    response = client.patch(f"/notes/{created['id']}", json={"collection_id": [other]})
    assert response.status_code == 422
    assert get_note(client, created["id"]) == created


def test_patch_unknown_collection_returns_422_and_changes_nothing(client, inbox):
    created = create_note(client, inbox)
    response = client.patch(
        f"/notes/{created['id']}", json={"body": "New", "collection_id": "no-such-collection"}
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Collection not found"}
    assert get_note(client, created["id"]) == created


def test_patch_unknown_tag_returns_422_creates_no_tag_and_changes_nothing(client, inbox):
    tag = make_tag(client, "t")
    created = create_note(client, inbox, tag_ids=[tag])
    tags_before = client.get("/tags").json()
    response = client.patch(
        f"/notes/{created['id']}", json={"body": "New body", "tag_ids": [tag, "new-tag"]}
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Tag not found"}
    assert client.get("/tags").json() == tags_before
    assert get_note(client, created["id"]) == created


def test_patch_duplicate_tag_ids_returns_422(client, inbox):
    tag = make_tag(client, "t")
    created = create_note(client, inbox)
    response = client.patch(f"/notes/{created['id']}", json={"tag_ids": [tag, tag]})
    assert response.status_code == 422
    assert response.json() == {"detail": "Duplicate tag id"}
    assert get_note(client, created["id"]) == created


def test_patch_tag_ids_replaces_the_list(client, inbox):
    a = make_tag(client, "a")
    b = make_tag(client, "b")
    c = make_tag(client, "c")
    created = create_note(client, inbox, tag_ids=[a, b])

    response = client.patch(f"/notes/{created['id']}", json={"tag_ids": [c]})
    assert response.status_code == 200
    assert response.json()["tag_ids"] == [c]

    response = client.patch(f"/notes/{created['id']}", json={"tag_ids": []})
    assert response.status_code == 200
    assert response.json()["tag_ids"] == []
    assert get_note(client, created["id"])["tag_ids"] == []


def test_patch_moves_note_to_nested_collection(client, inbox):
    parent = make_collection(client, "Parent")
    child = make_collection(client, "Child", parent_id=parent)
    created = create_note(client, inbox)
    response = client.patch(f"/notes/{created['id']}", json={"collection_id": child})
    assert response.status_code == 200
    assert response.json()["collection_id"] == child


@pytest.mark.parametrize("type_", TYPES)
def test_patch_same_type_is_accepted_with_no_effect(client, inbox, type_):
    created = create_note(client, inbox, type_)
    response = client.patch(f"/notes/{created['id']}", json={"type": type_})
    assert response.status_code == 200
    assert response.json() == created
    assert get_note(client, created["id"]) == created


@pytest.mark.parametrize("type_", TYPES)
def test_patch_different_type_returns_422(client, inbox, type_):
    created = create_note(client, inbox, type_)
    other_type = TYPES[(TYPES.index(type_) + 1) % len(TYPES)]
    response = client.patch(f"/notes/{created['id']}", json={"type": other_type, "body": "New"})
    assert response.status_code == 422
    assert response.json() == {"detail": "Note type cannot be changed"}
    assert get_note(client, created["id"]) == created


def test_patch_keeps_id_and_created_at(client, inbox):
    created = create_note(client, inbox)
    response = client.patch(f"/notes/{created['id']}", json={"body": "Changed"})
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["created_at"] == created["created_at"]


def test_patch_unknown_note_returns_404(client, inbox):
    response = client.patch(f"/notes/{uuid.uuid4()}", json={"body": "Valid", "collection_id": inbox})
    assert response.status_code == 404
    assert response.json() == {"detail": "Note not found"}


# --- Delete -------------------------------------------------------------------------------------


@pytest.mark.parametrize("type_", TYPES)
def test_delete_note(client, inbox, type_):
    created = create_note(client, inbox, type_)
    response = client.delete(f"/notes/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/notes/{created['id']}").status_code == 404

    second = client.delete(f"/notes/{created['id']}")
    assert second.status_code == 404
    assert second.json() == {"detail": "Note not found"}


def test_delete_unknown_note_returns_404(client):
    response = client.delete(f"/notes/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Note not found"}


def test_delete_keeps_collection_and_tags(client, inbox):
    tag = make_tag(client, "t")
    created = create_note(client, inbox, tag_ids=[tag])
    tags_before = client.get("/tags").json()
    collections_before = client.get("/collections").json()
    assert client.delete(f"/notes/{created['id']}").status_code == 204
    assert client.get("/tags").json() == tags_before
    assert client.get("/collections").json() == collections_before


# --- Interaction with collections ---------------------------------------------------------------


def test_collection_with_note_cannot_be_deleted_until_note_is_deleted(client, inbox):
    created = create_note(client, inbox)
    assert client.delete(f"/collections/{inbox}").status_code == 409
    assert client.delete(f"/notes/{created['id']}").status_code == 204
    assert client.delete(f"/collections/{inbox}").status_code == 204


def test_collection_can_be_deleted_after_note_is_moved(client, inbox):
    other = make_collection(client, "Other")
    created = create_note(client, inbox)
    assert client.delete(f"/collections/{inbox}").status_code == 409
    response = client.patch(f"/notes/{created['id']}", json={"collection_id": other})
    assert response.status_code == 200
    assert client.delete(f"/collections/{inbox}").status_code == 204
    assert client.delete(f"/collections/{other}").status_code == 409


# --- Structure ----------------------------------------------------------------------------------


def _variants(union_alias: Any) -> tuple[tuple[type, ...], Any]:
    union, field_info = get_args(union_alias)
    return get_args(union), field_info


@pytest.mark.parametrize(("alias", "base"), [(NoteCreate, NoteCreateBase), (NoteOut, NoteOutBase)])
def test_models_are_discriminated_unions_sharing_one_base(alias, base):
    variants, field_info = _variants(alias)
    assert field_info.discriminator == "type"
    assert len(variants) == 5
    assert {get_args(v.model_fields["type"].annotation)[0] for v in variants} == set(TYPES)
    for variant in variants:
        assert issubclass(variant, base)
        own = OWN_FIELDS[get_args(variant.model_fields["type"].annotation)[0]]
        assert set(variant.model_fields) == set(base.model_fields) | own
        # Shared fields live on the base only; each variant declares its `type` and its own fields.
        assert set(variant.__dict__.get("__annotations__", {})) == {"type"} | own


def test_create_variants_forbid_extra_fields():
    variants, _ = _variants(NoteCreate)
    for variant in variants:
        assert variant.model_config["extra"] == "forbid"
    assert set(NoteOutBase.model_fields) == FIELDS
    assert set(NoteCreateBase.model_fields) == {"type", "body", "collection_id", "tag_ids"}


def _resolve(spec: dict, schema: dict) -> dict:
    while "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        schema = spec["components"]["schemas"][name]
    return schema


def test_openapi_shows_discriminator_on_note_schemas(client):
    spec = client.get("/openapi.json").json()
    item = spec["paths"]["/notes/{note_id}"]
    schemas = [
        spec["paths"]["/notes"]["post"]["requestBody"]["content"]["application/json"]["schema"],
        spec["paths"]["/notes"]["post"]["responses"]["201"]["content"]["application/json"]["schema"],
        item["get"]["responses"]["200"]["content"]["application/json"]["schema"],
        item["patch"]["responses"]["200"]["content"]["application/json"]["schema"],
    ]
    for schema in schemas:
        schema = _resolve(spec, schema)
        assert len(schema["oneOf"]) == 5
        assert schema["discriminator"]["propertyName"] == "type"
        assert set(schema["discriminator"]["mapping"]) == set(TYPES)


def test_store_notes_holds_real_notes(client, store):
    assert isinstance(store.notes, InMemoryRepository)
    assert store.notes.list() == []
    inbox = make_collection(client, "Inbox")
    created = create_note(client, inbox)
    [stored] = store.notes.list()
    assert isinstance(stored, Note)
    assert stored.id == created["id"]
    assert stored.collection_id == inbox

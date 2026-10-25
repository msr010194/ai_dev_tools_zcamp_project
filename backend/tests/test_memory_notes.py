"""Tests for Memory fields and the resurfacing tracking fields on every note (#14)."""

from datetime import UTC, datetime

import pytest

from tests.note_helpers import TYPES, create_note, get_note, make_collection, note_payload, patch_note

OTHER_TYPES_FIELDS = {
    "entry_date": "2026-01-05T10:00:00Z",
    "mood": "calm",
    "prompt": "What went well?",
    "is_retrospective": True,
    "period": "weekly",
    "sub_kind": "written",
    "link": "https://example.com",
    "target_date": "2026-12-31",
    "state": "done",
    "checklist": [],
}
NON_MEMORY_TYPES = [t for t in TYPES if t != "memory"]


@pytest.fixture
def inbox(client) -> str:
    return make_collection(client, "Inbox")


# --- Memory fields: create ----------------------------------------------------------------------


def test_memory_defaults_to_null_when_and_where(client, inbox):
    note = create_note(client, inbox, "memory")
    assert note["when"] is None
    assert note["where"] is None


def test_memory_when_and_where_are_returned_as_sent(client, inbox):
    note = create_note(client, inbox, "memory", when="  summer 2019 ", where="Lisbon\n")
    assert note["when"] == "  summer 2019 "
    assert note["where"] == "Lisbon\n"
    assert get_note(client, note["id"]) == note


def test_memory_when_is_free_text_not_a_date(client, inbox):
    note = create_note(client, inbox, "memory", when="2019-07-01")
    assert note["when"] == "2019-07-01"


@pytest.mark.parametrize("field", ["when", "where"])
@pytest.mark.parametrize("value", ["", "   ", " \n\t", 123, ["a"], True, "x" * 201])
def test_memory_rejects_bad_text(client, inbox, field, value):
    response = client.post("/notes", json=note_payload(inbox, "memory", **{field: value}))
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["when", "where"])
def test_memory_text_length_limit(client, inbox, field):
    note = create_note(client, inbox, "memory", **{field: "x" * 200})
    assert note[field] == "x" * 200


@pytest.mark.parametrize("field", ["when", "where"])
def test_memory_accepts_explicit_null(client, inbox, field):
    note = create_note(client, inbox, "memory", **{field: None})
    assert note[field] is None


@pytest.mark.parametrize(("field", "value"), OTHER_TYPES_FIELDS.items())
def test_memory_rejects_other_types_fields(client, inbox, field, value):
    response = client.post("/notes", json=note_payload(inbox, "memory", **{field: value}))
    assert response.status_code == 422


@pytest.mark.parametrize("type_", NON_MEMORY_TYPES)
@pytest.mark.parametrize("field", ["when", "where"])
def test_other_types_reject_memory_fields_on_create(client, inbox, type_, field):
    response = client.post("/notes", json=note_payload(inbox, type_, **{field: "x"}))
    assert response.status_code == 422


@pytest.mark.parametrize("type_", NON_MEMORY_TYPES)
def test_other_types_never_return_memory_fields(client, inbox, type_):
    note = create_note(client, inbox, type_)
    assert "when" not in note
    assert "where" not in note
    assert "when" not in get_note(client, note["id"])


# --- Memory fields: update ----------------------------------------------------------------------


@pytest.mark.parametrize("field", ["when", "where"])
def test_patch_memory_field_alone(client, inbox, field):
    created = create_note(client, inbox, "memory", when="then", where="there")
    response = patch_note(client, created["id"], {field: "changed"})
    assert response.status_code == 200
    assert response.json() == {**created, field: "changed"}
    assert get_note(client, created["id"]) == response.json()


@pytest.mark.parametrize("field", ["when", "where"])
def test_patch_null_clears_memory_field(client, inbox, field):
    created = create_note(client, inbox, "memory", when="then", where="there")
    response = patch_note(client, created["id"], {field: None})
    assert response.status_code == 200
    assert response.json()[field] is None
    assert get_note(client, created["id"])[field] is None


@pytest.mark.parametrize("field", ["when", "where"])
@pytest.mark.parametrize("value", ["", "  ", 1, "x" * 201])
def test_patch_rejects_bad_memory_text(client, inbox, field, value):
    created = create_note(client, inbox, "memory", when="then")
    response = patch_note(client, created["id"], {field: value})
    assert response.status_code == 422
    assert get_note(client, created["id"]) == created


@pytest.mark.parametrize("type_", NON_MEMORY_TYPES)
@pytest.mark.parametrize("field", ["when", "where"])
def test_patch_memory_field_on_other_type_returns_422(client, inbox, type_, field):
    created = create_note(client, inbox, type_)
    response = patch_note(client, created["id"], {field: "x", "body": "Changed"})
    assert response.status_code == 422
    assert response.json() == {"detail": "Field not allowed for this note type"}
    assert get_note(client, created["id"]) == created


@pytest.mark.parametrize("type_", NON_MEMORY_TYPES)
def test_patch_null_memory_field_on_other_type_returns_422(client, inbox, type_):
    created = create_note(client, inbox, type_)
    response = patch_note(client, created["id"], {"where": None})
    assert response.status_code == 422
    assert response.json() == {"detail": "Field not allowed for this note type"}


def test_rejected_memory_patch_changes_nothing(client, inbox):
    created = create_note(client, inbox, "memory", when="then")
    response = patch_note(client, created["id"], {"body": "Changed", "when": "now", "where": ""})
    assert response.status_code == 422
    assert get_note(client, created["id"]) == created


# --- Resurfacing tracking fields ----------------------------------------------------------------


@pytest.mark.parametrize("type_", TYPES)
def test_new_note_has_tracking_defaults(client, inbox, type_):
    note = create_note(client, inbox, type_)
    assert note["last_resurfaced_at"] is None
    assert note["resurface_count"] == 0
    fetched = get_note(client, note["id"])
    assert fetched["last_resurfaced_at"] is None
    assert fetched["resurface_count"] == 0


@pytest.mark.parametrize("type_", TYPES)
@pytest.mark.parametrize(
    ("field", "value"),
    [("last_resurfaced_at", "2026-01-01T00:00:00Z"), ("last_resurfaced_at", None), ("resurface_count", 3)],
)
def test_tracking_fields_cannot_be_set_on_create(client, inbox, type_, field, value):
    response = client.post("/notes", json=note_payload(inbox, type_, **{field: value}))
    assert response.status_code == 422


@pytest.mark.parametrize("type_", TYPES)
@pytest.mark.parametrize(
    ("field", "value"),
    [("last_resurfaced_at", "2026-01-01T00:00:00Z"), ("resurface_count", 3), ("resurface_count", 0)],
)
def test_tracking_fields_cannot_be_set_on_patch(client, inbox, type_, field, value):
    created = create_note(client, inbox, type_)
    response = patch_note(client, created["id"], {field: value})
    assert response.status_code == 422
    assert get_note(client, created["id"]) == created


@pytest.mark.parametrize("type_", TYPES)
def test_patch_keeps_tracking_fields(client, store, inbox, type_):
    created = create_note(client, inbox, type_)
    [stored] = store.notes.list()
    seen_at = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    store.notes.update(stored.model_copy(update={"resurface_count": 4, "last_resurfaced_at": seen_at}))
    response = patch_note(client, created["id"], {"body": "Changed"})
    assert response.status_code == 200
    assert response.json()["resurface_count"] == 4
    assert datetime.fromisoformat(response.json()["last_resurfaced_at"]) == seen_at
    assert get_note(client, created["id"]) == response.json()

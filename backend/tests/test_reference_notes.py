"""Tests for Reference note fields (#12)."""

import pytest

from tests.note_helpers import TYPES, create_note, get_note, make_collection, note_payload, patch_note
from tests.error_helpers import error_body

SUB_KINDS = ["written", "visual", "audio"]
VALID_LINKS = [
    "https://example.com",
    "http://example.com/a/b?x=1#frag",
    "http://localhost:8000/x",
    "https://192.168.0.1/",
    "HTTPS://Example.com/Path",
]
INVALID_LINKS = [
    "",
    "   ",
    "example.com",
    "www.example.com",
    "ftp://example.com",
    "mailto:a@b.c",
    "javascript:alert(1)",
    "https://",
    "https:///path",
    "https://exa mple.com",
    "https://example.com/\n",
    "http://[::1",
    42,
    ["https://example.com"],
    True,
]
OTHER_TYPES_FIELDS = {
    "entry_date": "2026-01-05T10:00:00Z",
    "mood": "calm",
    "prompt": "What went well?",
    "is_retrospective": True,
    "period": "weekly",
    "target_date": "2026-12-31",
    "state": "done",
    "checklist": [],
    "when": "summer 2019",
    "where": "Lisbon",
}
NON_REFERENCE_TYPES = [t for t in TYPES if t != "reference"]


@pytest.fixture
def inbox(client) -> str:
    return make_collection(client, "Inbox")


@pytest.fixture
def reference(client, inbox) -> dict:
    return create_note(client, inbox, "reference", sub_kind="visual", link="https://example.com")


def link_of_length(length: int) -> str:
    prefix = "https://example.com/"
    return prefix + "a" * (length - len(prefix))


# --- Create -------------------------------------------------------------------------------------


def test_reference_defaults(client, inbox):
    note = create_note(client, inbox, "reference")
    assert note["sub_kind"] == "written"
    assert note["link"] is None


@pytest.mark.parametrize("sub_kind", SUB_KINDS)
def test_each_sub_kind_is_accepted(client, inbox, sub_kind):
    note = create_note(client, inbox, "reference", sub_kind=sub_kind)
    assert note["sub_kind"] == sub_kind
    assert get_note(client, note["id"])["sub_kind"] == sub_kind


@pytest.mark.parametrize("value", ["video", "Audio", "WRITTEN", "", None, 1, ["written"]])
def test_bad_sub_kind_is_rejected(client, inbox, value):
    response = client.post("/notes", json=note_payload(inbox, "reference", sub_kind=value))
    assert response.status_code == 422


@pytest.mark.parametrize("link", VALID_LINKS)
def test_valid_links_are_returned_unchanged(client, inbox, link):
    note = create_note(client, inbox, "reference", link=link)
    assert note["link"] == link
    assert get_note(client, note["id"])["link"] == link


@pytest.mark.parametrize("link", INVALID_LINKS)
def test_invalid_links_are_rejected(client, inbox, link):
    response = client.post("/notes", json=note_payload(inbox, "reference", link=link))
    assert response.status_code == 422


def test_link_length_limit(client, inbox):
    assert create_note(client, inbox, "reference", link=link_of_length(2048))["link"] == link_of_length(2048)
    response = client.post("/notes", json=note_payload(inbox, "reference", link=link_of_length(2049)))
    assert response.status_code == 422


def test_explicit_null_link(client, inbox):
    assert create_note(client, inbox, "reference", link=None)["link"] is None


@pytest.mark.parametrize(("field", "value"), OTHER_TYPES_FIELDS.items())
def test_reference_rejects_other_types_fields(client, inbox, field, value):
    response = client.post("/notes", json=note_payload(inbox, "reference", **{field: value}))
    assert response.status_code == 422


@pytest.mark.parametrize("type_", NON_REFERENCE_TYPES)
@pytest.mark.parametrize(("field", "value"), [("sub_kind", "written"), ("link", "https://example.com")])
def test_other_types_reject_reference_fields(client, inbox, type_, field, value):
    response = client.post("/notes", json=note_payload(inbox, type_, **{field: value}))
    assert response.status_code == 422


@pytest.mark.parametrize("type_", NON_REFERENCE_TYPES)
def test_other_types_never_return_reference_fields(client, inbox, type_):
    note = create_note(client, inbox, type_)
    assert "sub_kind" not in note
    assert "link" not in note
    assert "link" not in get_note(client, note["id"])


# --- Update -------------------------------------------------------------------------------------


def test_patch_sub_kind_alone(client, reference):
    response = patch_note(client, reference["id"], {"sub_kind": "audio"})
    assert response.status_code == 200
    assert response.json() == {**reference, "sub_kind": "audio"}
    assert get_note(client, reference["id"]) == response.json()


def test_patch_link_alone(client, reference):
    response = patch_note(client, reference["id"], {"link": "http://other.example/x"})
    assert response.status_code == 200
    assert response.json() == {**reference, "link": "http://other.example/x"}


def test_patch_null_clears_link(client, reference):
    response = patch_note(client, reference["id"], {"link": None})
    assert response.status_code == 200
    assert response.json()["link"] is None
    assert get_note(client, reference["id"])["link"] is None


def test_patch_null_sub_kind_is_rejected(client, reference):
    response = patch_note(client, reference["id"], {"sub_kind": None})
    assert response.status_code == 422
    assert get_note(client, reference["id"]) == reference


@pytest.mark.parametrize("value", ["video", "Audio", "", 1])
def test_patch_bad_sub_kind_is_rejected(client, reference, value):
    response = patch_note(client, reference["id"], {"sub_kind": value})
    assert response.status_code == 422
    assert get_note(client, reference["id"]) == reference


@pytest.mark.parametrize("link", [*INVALID_LINKS, link_of_length(2049)])
def test_patch_invalid_link_is_rejected(client, reference, link):
    response = patch_note(client, reference["id"], {"link": link})
    assert response.status_code == 422
    assert get_note(client, reference["id"]) == reference


def test_rejected_patch_leaves_shared_fields_unchanged(client, reference):
    response = patch_note(client, reference["id"], {"body": "Changed", "link": "example.com"})
    assert response.status_code == 422
    assert get_note(client, reference["id"]) == reference


@pytest.mark.parametrize("type_", NON_REFERENCE_TYPES)
@pytest.mark.parametrize(("field", "value"), [("sub_kind", "audio"), ("link", "https://example.com")])
def test_patch_reference_field_on_other_type(client, inbox, type_, field, value):
    note = create_note(client, inbox, type_)
    response = patch_note(client, note["id"], {field: value})
    assert response.status_code == 422
    assert response.json() == error_body("field_not_allowed", "Field not allowed for this note type")
    assert get_note(client, note["id"]) == note

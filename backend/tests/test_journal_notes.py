"""Tests for Journal note fields (#11)."""

from datetime import UTC, datetime, timedelta

import pytest

from tests.note_helpers import TYPES, create_note, get_note, make_collection, note_payload, patch_note

JOURNAL_FIELDS = {
    "entry_date": "2026-01-05T10:00:00Z",
    "mood": "calm",
    "prompt": "What went well?",
    "is_retrospective": True,
    "period": "weekly",
}
OTHER_TYPES_FIELDS = {
    "sub_kind": "written",
    "link": "https://example.com",
    "target_date": "2026-12-31",
    "state": "done",
    "checklist": [],
    "when": "summer 2019",
    "where": "Lisbon",
}
NON_JOURNAL_TYPES = [t for t in TYPES if t != "journal"]


@pytest.fixture
def inbox(client) -> str:
    return make_collection(client, "Inbox")


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def reject_post(client, inbox, **fields) -> None:
    response = client.post("/notes", json=note_payload(inbox, "journal", **fields))
    assert response.status_code == 422, response.text


# --- Create -------------------------------------------------------------------------------------


def test_journal_defaults(client, inbox):
    note = create_note(client, inbox, "journal")
    assert note["entry_date"] == note["created_at"]
    assert note["mood"] is None
    assert note["prompt"] is None
    assert note["is_retrospective"] is False
    assert note["period"] is None


def test_journal_with_all_fields(client, inbox):
    note = create_note(
        client,
        inbox,
        "journal",
        entry_date="2026-01-05T12:30:00+02:00",
        mood=" calm ",
        prompt="What went well?\n",
        is_retrospective=True,
        period="monthly",
    )
    assert parse(note["entry_date"]) == datetime(2026, 1, 5, 10, 30, tzinfo=UTC)
    assert parse(note["entry_date"]).utcoffset() == timedelta(0)
    assert note["mood"] == " calm "
    assert note["prompt"] == "What went well?\n"
    assert note["is_retrospective"] is True
    assert note["period"] == "monthly"
    assert get_note(client, note["id"]) == note


@pytest.mark.parametrize("entry_date", ["2000-01-01T00:00:00Z", "2100-12-31T23:59:59Z"])
def test_entry_date_in_past_or_future_is_accepted(client, inbox, entry_date):
    note = create_note(client, inbox, "journal", entry_date=entry_date)
    assert parse(note["entry_date"]) == parse(entry_date)


@pytest.mark.parametrize(
    "value",
    [
        "2026-01-05T10:00:00",
        "2026-01-05",
        "yesterday",
        "",
        None,
        1700000000,
        "1700000000",
        "1700000000.5",
        True,
        "9999-12-31T23:00:00-05:00",
        "0001-01-01T00:30:00+01:00",
    ],
)
def test_bad_entry_date_is_rejected(client, inbox, value):
    reject_post(client, inbox, entry_date=value)


@pytest.mark.parametrize(
    ("field", "limit"), [("mood", 100), ("prompt", 500)]
)
def test_text_fields_length_limit(client, inbox, field, limit):
    assert create_note(client, inbox, "journal", **{field: "x" * limit})[field] == "x" * limit
    reject_post(client, inbox, **{field: "x" * (limit + 1)})


@pytest.mark.parametrize("field", ["mood", "prompt"])
@pytest.mark.parametrize("value", ["", "   ", "\n\t", 5, ["a"], True])
def test_bad_text_fields_are_rejected(client, inbox, field, value):
    reject_post(client, inbox, **{field: value})


@pytest.mark.parametrize("value", ["true", 1, 0, None])
def test_bad_is_retrospective_is_rejected(client, inbox, value):
    reject_post(client, inbox, is_retrospective=value)


@pytest.mark.parametrize("value", ["daily", "Weekly", "", 1])
def test_bad_period_is_rejected(client, inbox, value):
    reject_post(client, inbox, is_retrospective=True, period=value)


def test_retrospective_without_period(client, inbox):
    note = create_note(client, inbox, "journal", is_retrospective=True)
    assert note["is_retrospective"] is True
    assert note["period"] is None


def test_retrospective_with_period(client, inbox):
    note = create_note(client, inbox, "journal", is_retrospective=True, period="monthly")
    assert note["period"] == "monthly"


@pytest.mark.parametrize("retro", [False, None, "omitted"])
def test_period_without_retrospective_is_rejected(client, inbox, retro):
    fields = {"period": "weekly"}
    if retro != "omitted":
        fields["is_retrospective"] = retro
    reject_post(client, inbox, **fields)


@pytest.mark.parametrize(("field", "value"), OTHER_TYPES_FIELDS.items())
def test_journal_rejects_other_types_fields(client, inbox, field, value):
    reject_post(client, inbox, **{field: value})


@pytest.mark.parametrize("type_", NON_JOURNAL_TYPES)
@pytest.mark.parametrize(("field", "value"), JOURNAL_FIELDS.items())
def test_other_types_reject_journal_fields(client, inbox, type_, field, value):
    response = client.post("/notes", json=note_payload(inbox, type_, **{field: value}))
    assert response.status_code == 422


@pytest.mark.parametrize("type_", NON_JOURNAL_TYPES)
def test_other_types_never_return_journal_fields(client, inbox, type_):
    note = create_note(client, inbox, type_)
    assert not set(JOURNAL_FIELDS) & set(note)
    assert not set(JOURNAL_FIELDS) & set(get_note(client, note["id"]))


# --- Update -------------------------------------------------------------------------------------


@pytest.fixture
def journal(client, inbox) -> dict:
    return create_note(client, inbox, "journal", mood="calm", entry_date="2026-01-05T10:00:00Z")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("entry_date", "2026-02-01T08:00:00Z"),
        ("mood", "tired"),
        ("is_retrospective", True),
        ("prompt", "A new prompt"),
    ],
)
def test_patch_journal_field_alone(client, journal, field, value):
    response = patch_note(client, journal["id"], {field: value})
    assert response.status_code == 200, response.text
    updated = response.json()
    for name in journal:
        if name != field:
            assert updated[name] == journal[name]
    if field == "entry_date":
        assert parse(updated[field]) == parse(value)
    else:
        assert updated[field] == value
    assert get_note(client, journal["id"]) == updated


def test_patch_period_on_retrospective(client, inbox):
    note = create_note(client, inbox, "journal", is_retrospective=True)
    response = patch_note(client, note["id"], {"period": "weekly"})
    assert response.status_code == 200
    assert response.json()["period"] == "weekly"


def test_patch_null_clears_mood(client, journal):
    response = patch_note(client, journal["id"], {"mood": None})
    assert response.status_code == 200
    assert response.json()["mood"] is None
    assert get_note(client, journal["id"])["mood"] is None


def test_patch_null_clears_period(client, inbox):
    note = create_note(client, inbox, "journal", is_retrospective=True, period="weekly")
    response = patch_note(client, note["id"], {"period": None})
    assert response.status_code == 200
    assert response.json()["period"] is None
    assert response.json()["is_retrospective"] is True


@pytest.mark.parametrize("field", ["entry_date", "is_retrospective"])
def test_patch_null_on_required_field_is_rejected(client, journal, field):
    response = patch_note(client, journal["id"], {field: None})
    assert response.status_code == 422
    assert get_note(client, journal["id"]) == journal


@pytest.mark.parametrize(
    "payload",
    [
        {"mood": ""},
        {"mood": "  "},
        {"mood": "x" * 101},
        {"prompt": "x" * 501},
        {"prompt": " "},
        {"entry_date": "2026-01-05T10:00:00"},
        {"entry_date": "2026-01-05"},
        {"entry_date": "1700000000"},
        {"entry_date": "9999-12-31T23:00:00-05:00"},
        {"period": "daily"},
        {"is_retrospective": "true"},
    ],
)
def test_patch_rejects_invalid_values(client, journal, payload):
    response = patch_note(client, journal["id"], payload)
    assert response.status_code == 422
    assert get_note(client, journal["id"]) == journal


def test_prompt_can_be_set_later_once(client, journal):
    assert journal["prompt"] is None
    response = patch_note(client, journal["id"], {"prompt": "Later prompt"})
    assert response.status_code == 200
    assert response.json()["prompt"] == "Later prompt"

    response = patch_note(client, journal["id"], {"prompt": "Changed prompt"})
    assert response.status_code == 422
    assert response.json() == {"detail": "Prompt cannot be changed once set"}
    assert get_note(client, journal["id"])["prompt"] == "Later prompt"


@pytest.mark.parametrize("value", ["Different", None])
def test_set_prompt_cannot_be_changed_or_cleared(client, inbox, value):
    note = create_note(client, inbox, "journal", prompt="Original")
    response = patch_note(client, note["id"], {"prompt": value, "body": "New body"})
    assert response.status_code == 422
    assert response.json() == {"detail": "Prompt cannot be changed once set"}
    assert get_note(client, note["id"]) == note


def test_same_prompt_is_a_no_op(client, inbox):
    note = create_note(client, inbox, "journal", prompt="Original")
    response = patch_note(client, note["id"], {"prompt": "Original"})
    assert response.status_code == 200
    assert response.json() == note


def test_null_prompt_on_note_without_prompt_is_accepted(client, journal):
    response = patch_note(client, journal["id"], {"prompt": None})
    assert response.status_code == 200
    assert response.json() == journal


def test_turning_off_retrospective_with_period_is_rejected(client, inbox):
    note = create_note(client, inbox, "journal", is_retrospective=True, period="monthly")
    response = patch_note(client, note["id"], {"is_retrospective": False})
    assert response.status_code == 422
    assert response.json() == {"detail": "Period requires is_retrospective"}
    assert get_note(client, note["id"]) == note


def test_turning_off_retrospective_and_clearing_period(client, inbox):
    note = create_note(client, inbox, "journal", is_retrospective=True, period="monthly")
    response = patch_note(client, note["id"], {"is_retrospective": False, "period": None})
    assert response.status_code == 200
    assert response.json()["is_retrospective"] is False
    assert response.json()["period"] is None


def test_period_on_non_retrospective_is_rejected(client, journal):
    response = patch_note(client, journal["id"], {"period": "weekly"})
    assert response.status_code == 422
    assert response.json() == {"detail": "Period requires is_retrospective"}
    assert get_note(client, journal["id"]) == journal


def test_period_and_retrospective_together(client, journal):
    response = patch_note(client, journal["id"], {"is_retrospective": True, "period": "weekly"})
    assert response.status_code == 200
    assert response.json()["period"] == "weekly"


def test_rejected_patch_leaves_shared_fields_unchanged(client, inbox):
    note = create_note(client, inbox, "journal", prompt="Original")
    response = patch_note(client, note["id"], {"body": "Changed", "mood": "ok", "prompt": "New"})
    assert response.status_code == 422
    assert get_note(client, note["id"]) == note


@pytest.mark.parametrize("type_", NON_JOURNAL_TYPES)
@pytest.mark.parametrize(("field", "value"), JOURNAL_FIELDS.items())
def test_patch_journal_field_on_other_type(client, inbox, type_, field, value):
    note = create_note(client, inbox, type_)
    response = patch_note(client, note["id"], {field: value})
    assert response.status_code == 422
    assert response.json() == {"detail": "Field not allowed for this note type"}
    assert get_note(client, note["id"]) == note

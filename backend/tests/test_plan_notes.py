"""Tests for Plan note fields and the checklist (#13)."""

import pytest

from tests.note_helpers import TYPES, create_note, get_note, make_collection, note_payload, patch_note

STATES = ["not_started", "in_progress", "done", "abandoned"]
OTHER_TYPES_FIELDS = {
    "entry_date": "2026-01-05T10:00:00Z",
    "mood": "calm",
    "prompt": "What went well?",
    "is_retrospective": True,
    "period": "weekly",
    "sub_kind": "written",
    "link": "https://example.com",
    "when": "summer 2019",
    "where": "Lisbon",
}
PLAN_FIELDS = {"target_date": "2026-12-31", "state": "done", "checklist": []}
NON_PLAN_TYPES = [t for t in TYPES if t != "plan"]


@pytest.fixture
def inbox(client) -> str:
    return make_collection(client, "Inbox")


def items(*texts_and_done: tuple[str, bool]) -> list[dict]:
    return [{"text": text, "done": done} for text, done in texts_and_done]


def with_positions(checklist: list[dict]) -> list[dict]:
    return [{**item, "position": i} for i, item in enumerate(checklist)]


def without_positions(checklist: list[dict]) -> list[dict]:
    return [{"text": item["text"], "done": item["done"]} for item in checklist]


def reject_post(client, inbox, **fields) -> None:
    response = client.post("/notes", json=note_payload(inbox, "plan", **fields))
    assert response.status_code == 422, response.text


@pytest.fixture
def plan(client, inbox) -> dict:
    checklist = items(("Book flights", False), ("Pack", False), ("Go", False))
    return create_note(client, inbox, "plan", target_date="2026-06-01", checklist=checklist)


# --- Create -------------------------------------------------------------------------------------


def test_plan_defaults(client, inbox):
    note = create_note(client, inbox, "plan")
    assert note["target_date"] is None
    assert note["state"] == "not_started"
    assert note["checklist"] == []


@pytest.mark.parametrize("state", STATES)
def test_each_state_is_accepted(client, inbox, state):
    note = create_note(client, inbox, "plan", state=state)
    assert note["state"] == state
    assert get_note(client, note["id"])["state"] == state


@pytest.mark.parametrize("value", ["blocked", "Done", "", None, 1])
def test_bad_state_is_rejected(client, inbox, value):
    reject_post(client, inbox, state=value)


@pytest.mark.parametrize("value", ["2026-12-31", "2001-01-01"])
def test_target_date_is_returned_as_sent(client, inbox, value):
    note = create_note(client, inbox, "plan", target_date=value)
    assert note["target_date"] == value
    assert get_note(client, note["id"])["target_date"] == value


@pytest.mark.parametrize(
    "value",
    ["2026-12-31T10:00:00Z", "2026-12-31T00:00:00", "2026-02-30", "31/12/2026", "2026-1-5", "", 20261231],
)
def test_bad_target_date_is_rejected(client, inbox, value):
    reject_post(client, inbox, target_date=value)


def test_explicit_null_target_date(client, inbox):
    assert create_note(client, inbox, "plan", target_date=None)["target_date"] is None


def test_checklist_keeps_order_with_positions(client, inbox):
    checklist = items(("First", False), ("Second", True), ("Third", False))
    note = create_note(client, inbox, "plan", checklist=checklist)
    assert note["checklist"] == with_positions(checklist)
    assert get_note(client, note["id"])["checklist"] == with_positions(checklist)


def test_item_done_defaults_to_false(client, inbox):
    note = create_note(client, inbox, "plan", checklist=[{"text": "Only text"}])
    assert note["checklist"] == [{"text": "Only text", "done": False, "position": 0}]


def test_item_text_is_kept_as_sent(client, inbox):
    note = create_note(client, inbox, "plan", checklist=[{"text": "  spaced \n"}])
    assert note["checklist"][0]["text"] == "  spaced \n"


@pytest.mark.parametrize(
    "item",
    [
        {},
        {"done": True},
        {"text": ""},
        {"text": "   "},
        {"text": "x" * 501},
        {"text": 5},
        {"text": None},
        {"text": "ok", "done": "true"},
        {"text": "ok", "done": 1},
        {"text": "ok", "done": None},
        {"text": "ok", "position": 0},
        {"text": "ok", "id": "abc"},
        "just text",
    ],
)
def test_bad_item_is_rejected(client, inbox, item):
    reject_post(client, inbox, checklist=[item])


def test_item_text_length_limit(client, inbox):
    note = create_note(client, inbox, "plan", checklist=[{"text": "x" * 500}])
    assert note["checklist"][0]["text"] == "x" * 500


def test_duplicate_item_texts_are_kept(client, inbox):
    checklist = items(("Same", False), ("Same", False))
    note = create_note(client, inbox, "plan", checklist=checklist)
    assert note["checklist"] == with_positions(checklist)


def test_checklist_item_limit(client, inbox):
    hundred = [{"text": f"Item {i}"} for i in range(100)]
    note = create_note(client, inbox, "plan", checklist=hundred)
    assert len(note["checklist"]) == 100
    assert note["checklist"][-1]["position"] == 99
    reject_post(client, inbox, checklist=[*hundred, {"text": "One too many"}])


@pytest.mark.parametrize("value", [None, "item", {"text": "a"}, 1])
def test_bad_checklist_is_rejected(client, inbox, value):
    reject_post(client, inbox, checklist=value)


@pytest.mark.parametrize(("field", "value"), OTHER_TYPES_FIELDS.items())
def test_plan_rejects_other_types_fields(client, inbox, field, value):
    reject_post(client, inbox, **{field: value})


@pytest.mark.parametrize("type_", NON_PLAN_TYPES)
@pytest.mark.parametrize(("field", "value"), PLAN_FIELDS.items())
def test_other_types_reject_plan_fields(client, inbox, type_, field, value):
    response = client.post("/notes", json=note_payload(inbox, type_, **{field: value}))
    assert response.status_code == 422


@pytest.mark.parametrize("type_", NON_PLAN_TYPES)
def test_other_types_never_return_plan_fields(client, inbox, type_):
    note = create_note(client, inbox, type_)
    assert not set(PLAN_FIELDS) & set(note)
    assert not set(PLAN_FIELDS) & set(get_note(client, note["id"]))


# --- Update -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [("target_date", "2027-01-01"), ("state", "in_progress"), ("checklist", items(("New", True)))],
)
def test_patch_plan_field_alone(client, plan, field, value):
    response = patch_note(client, plan["id"], {field: value})
    assert response.status_code == 200, response.text
    expected = {**plan, field: with_positions(value) if field == "checklist" else value}
    assert response.json() == expected
    assert get_note(client, plan["id"]) == expected


def test_patch_null_clears_target_date(client, plan):
    response = patch_note(client, plan["id"], {"target_date": None})
    assert response.status_code == 200
    assert response.json()["target_date"] is None


@pytest.mark.parametrize("field", ["state", "checklist"])
def test_patch_null_on_required_field_is_rejected(client, plan, field):
    response = patch_note(client, plan["id"], {field: None})
    assert response.status_code == 422
    assert get_note(client, plan["id"]) == plan


@pytest.mark.parametrize("start", STATES)
@pytest.mark.parametrize("end", STATES)
def test_any_state_can_move_to_any_state(client, inbox, start, end):
    note = create_note(client, inbox, "plan", state=start)
    response = patch_note(client, note["id"], {"state": end})
    assert response.status_code == 200
    assert response.json()["state"] == end


def test_add_item(client, plan):
    checklist = [*without_positions(plan["checklist"]), {"text": "Come back", "done": False}]
    response = patch_note(client, plan["id"], {"checklist": checklist})
    assert response.status_code == 200
    assert response.json()["checklist"] == with_positions(checklist)
    assert response.json()["checklist"][-1] == {"text": "Come back", "done": False, "position": 3}


def test_toggle_item(client, plan):
    checklist = without_positions(plan["checklist"])
    checklist[1]["done"] = True
    response = patch_note(client, plan["id"], {"checklist": checklist})
    assert response.status_code == 200
    result = response.json()["checklist"]
    assert [item["done"] for item in result] == [False, True, False]
    assert [item["text"] for item in result] == [item["text"] for item in plan["checklist"]]


def test_reorder_items(client, plan):
    checklist = list(reversed(without_positions(plan["checklist"])))
    response = patch_note(client, plan["id"], {"checklist": checklist})
    assert response.status_code == 200
    assert response.json()["checklist"] == with_positions(checklist)
    assert [item["text"] for item in response.json()["checklist"]] == ["Go", "Pack", "Book flights"]


def test_remove_item_renumbers_positions(client, plan):
    checklist = without_positions(plan["checklist"])
    del checklist[0]
    response = patch_note(client, plan["id"], {"checklist": checklist})
    assert response.status_code == 200
    assert response.json()["checklist"] == [
        {"text": "Pack", "done": False, "position": 0},
        {"text": "Go", "done": False, "position": 1},
    ]


def test_empty_checklist(client, plan):
    response = patch_note(client, plan["id"], {"checklist": []})
    assert response.status_code == 200
    assert response.json()["checklist"] == []
    assert get_note(client, plan["id"])["checklist"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {"state": "blocked"},
        {"target_date": "2026-02-30"},
        {"target_date": "2026-12-31T10:00:00Z"},
        {"checklist": [{"text": ""}]},
        {"checklist": [{"text": "ok", "position": 0}]},
        {"checklist": [{"text": "ok", "done": "yes"}]},
        {"checklist": [{"text": f"{i}"} for i in range(101)]},
        {"checklist": "item"},
    ],
)
def test_patch_rejects_invalid_values(client, plan, payload):
    response = patch_note(client, plan["id"], payload)
    assert response.status_code == 422
    assert get_note(client, plan["id"]) == plan


def test_rejected_patch_leaves_checklist_and_shared_fields_unchanged(client, plan):
    response = patch_note(
        client, plan["id"], {"body": "Changed", "checklist": [], "collection_id": "no-such-collection"}
    )
    assert response.status_code == 422
    assert get_note(client, plan["id"]) == plan


@pytest.mark.parametrize("type_", NON_PLAN_TYPES)
@pytest.mark.parametrize(("field", "value"), PLAN_FIELDS.items())
def test_patch_plan_field_on_other_type(client, inbox, type_, field, value):
    note = create_note(client, inbox, type_)
    response = patch_note(client, note["id"], {field: value})
    assert response.status_code == 422
    assert response.json() == {"detail": "Field not allowed for this note type"}
    assert get_note(client, note["id"]) == note


# --- Delete -------------------------------------------------------------------------------------


def test_delete_plan_removes_its_checklist(client, store, plan):
    assert client.delete(f"/notes/{plan['id']}").status_code == 204
    assert client.get(f"/notes/{plan['id']}").status_code == 404
    assert store.notes.list() == []

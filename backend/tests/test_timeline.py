"""Tests for `GET /timeline` (#15): ordering, cursor pagination and filters."""

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.timeline import TimelineFilters
from tests.note_helpers import TYPES, create_note, make_collection, make_tag, patch_note

T0 = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def inbox(client) -> str:
    return make_collection(client, "Inbox")


def add_note(client, store, collection_id: str, minutes: float, type_: str = "idea", **extra) -> str:
    """Create a note through the API, then pin its `created_at` to T0 + `minutes`."""
    note_id = create_note(client, collection_id, type_, **extra)["id"]
    stored = store.notes.get(note_id)
    store.notes.update(stored.model_copy(update={"created_at": T0 + timedelta(minutes=minutes)}))
    return note_id


def timeline(client, **params) -> dict:
    response = client.get("/timeline", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def ids(page: dict) -> list[str]:
    return [item["id"] for item in page["items"]]


def all_ids(client, **params) -> list[str]:
    """Follow `next_cursor` to the end and collect every id."""
    collected: list[str] = []
    page = timeline(client, **params)
    collected += ids(page)
    while page["next_cursor"] is not None:
        page = timeline(client, **params, cursor=page["next_cursor"])
        collected += ids(page)
    return collected


def tamper(cursor: str) -> str:
    middle = len(cursor) // 2
    replacement = "A" if cursor[middle] != "A" else "B"
    return cursor[:middle] + replacement + cursor[middle + 1 :]


# --- Ordering and shape -------------------------------------------------------------------------


def test_empty_timeline(client):
    assert timeline(client) == {"items": [], "next_cursor": None}


def test_all_types_newest_first(client, store, inbox):
    created = [add_note(client, store, inbox, minutes, type_) for minutes, type_ in enumerate(TYPES)]
    page = timeline(client)
    assert ids(page) == list(reversed(created))
    assert {item["type"] for item in page["items"]} == set(TYPES)


def test_ties_are_ordered_by_id_descending(client, store, inbox):
    tied = [add_note(client, store, inbox, 5) for _ in range(4)]
    newer = add_note(client, store, inbox, 10)
    older = add_note(client, store, inbox, 1)
    expected = [newer, *sorted(tied, reverse=True), older]
    assert ids(timeline(client)) == expected
    assert ids(timeline(client)) == expected
    assert all_ids(client, limit=1) == expected


def test_items_match_get_note(client, store, inbox):
    tag = make_tag(client, "t")
    add_note(client, store, inbox, 1, "plan", tag_ids=[tag], checklist=[{"text": "a"}])
    add_note(client, store, inbox, 2, "journal", mood="ok")
    for item in timeline(client)["items"]:
        assert item == client.get(f"/notes/{item['id']}").json()


# --- Pagination ---------------------------------------------------------------------------------


def test_default_page_size_and_following_cursors(client, store, inbox):
    created = [add_note(client, store, inbox, minutes) for minutes in range(45)]
    newest_first = list(reversed(created))

    first = timeline(client)
    assert ids(first) == newest_first[:20]
    assert first["next_cursor"] is not None
    second = timeline(client, cursor=first["next_cursor"])
    assert ids(second) == newest_first[20:40]
    assert second["next_cursor"] is not None
    third = timeline(client, cursor=second["next_cursor"])
    assert ids(third) == newest_first[40:]
    assert third["next_cursor"] is None


def test_exactly_one_full_page_has_no_next_cursor(client, store, inbox):
    for minutes in range(20):
        add_note(client, store, inbox, minutes)
    page = timeline(client)
    assert len(page["items"]) == 20
    assert page["next_cursor"] is None


@pytest.mark.parametrize("limit", [1, 100])
def test_limit_bounds(client, store, inbox, limit):
    created = [add_note(client, store, inbox, minutes) for minutes in range(101)]
    page = timeline(client, limit=limit)
    assert ids(page) == list(reversed(created))[:limit]
    assert page["next_cursor"] is not None


@pytest.mark.parametrize("limit", ["0", "101", "-1", "abc", "1.5"])
def test_bad_limit_is_rejected(client, limit):
    assert client.get("/timeline", params={"limit": limit}).status_code == 422


def test_notes_created_after_first_page_do_not_appear_later(client, store, inbox):
    created = [add_note(client, store, inbox, minutes) for minutes in range(5)]
    first = timeline(client, limit=2)
    assert ids(first) == [created[4], created[3]]
    newer = [add_note(client, store, inbox, 100), create_note(client, inbox)["id"]]

    rest: list[str] = []
    page = first
    while page["next_cursor"] is not None:
        page = timeline(client, limit=2, cursor=page["next_cursor"])
        rest += ids(page)
    assert rest == [created[2], created[1], created[0]]
    assert not set(newer) & set(rest)


def test_note_deleted_between_pages_skips_nothing_else(client, store, inbox):
    created = [add_note(client, store, inbox, minutes) for minutes in range(6)]
    first = timeline(client, limit=2)
    assert client.delete(f"/notes/{created[4]}").status_code == 204
    assert client.delete(f"/notes/{created[2]}").status_code == 204
    second = timeline(client, limit=2, cursor=first["next_cursor"])
    assert ids(second) == [created[3], created[1]]
    third = timeline(client, limit=2, cursor=second["next_cursor"])
    assert ids(third) == [created[0]]
    assert third["next_cursor"] is None


@pytest.mark.parametrize(
    "cursor",
    ["", "not-a-cursor", "!!!", base64.urlsafe_b64encode(b'{"t":"x","i":"y","f":"z"}').decode()],
)
def test_malformed_cursor_is_rejected(client, store, inbox, cursor):
    add_note(client, store, inbox, 1)
    response = client.get("/timeline", params={"cursor": cursor})
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid cursor"}


def test_tampered_cursor_is_rejected(client, store, inbox):
    for minutes in range(3):
        add_note(client, store, inbox, minutes)
    cursor = timeline(client, limit=1)["next_cursor"]
    response = client.get("/timeline", params={"limit": 1, "cursor": tamper(cursor)})
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid cursor"}


def _sign(body: str, key: bytes) -> str:
    signature = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()[:16]
    return base64.urlsafe_b64encode((signature + body).encode()).decode().rstrip("=")


def test_cursor_forged_without_the_secret_is_rejected(client, store, inbox):
    add_note(client, store, inbox, 1)
    body = json.dumps({"f": TimelineFilters().fingerprint(), "i": "x", "t": T0.isoformat()})
    forged = base64.urlsafe_b64encode(
        (hashlib.sha256(body.encode()).hexdigest()[:16] + body).encode()
    ).decode()
    response = client.get("/timeline", params={"cursor": forged})
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid cursor"}


@pytest.mark.parametrize(
    "body", ["[" * 5000 + "]" * 5000, "[1, 2]", '"text"', "null", '{"t": 1, "i": "x", "f": "y"}']
)
def test_signed_but_malformed_cursor_body_is_rejected(app, client, body):
    cursor = _sign(body, app.state.settings.cursor_secret.encode())
    response = client.get("/timeline", params={"cursor": cursor})
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid cursor"}


def test_cursor_from_another_app_instance_is_rejected(client, store, inbox):
    for minutes in range(3):
        add_note(client, store, inbox, minutes)
    with TestClient(create_app()) as other_client:
        other_inbox = make_collection(other_client, "Inbox")
        for _ in range(3):
            create_note(other_client, other_inbox)
        foreign = other_client.get("/timeline", params={"limit": 1}).json()["next_cursor"]
    response = client.get("/timeline", params={"limit": 1, "cursor": foreign})
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid cursor"}


def test_shared_cursor_secret_makes_cursors_portable(monkeypatch):
    monkeypatch.setenv("NOTES_CURSOR_SECRET", "shared-secret")
    first_app, second_app = create_app(), create_app()
    second_app.state.store = first_app.state.store
    with TestClient(first_app) as first, TestClient(second_app) as second:
        inbox = make_collection(first, "Inbox")
        for _ in range(3):
            create_note(first, inbox)
        cursor = first.get("/timeline", params={"limit": 1}).json()["next_cursor"]
        response = second.get("/timeline", params={"limit": 1, "cursor": cursor})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


@pytest.mark.parametrize(
    "other_filters",
    [{"type": "plan"}, {"untagged": "true"}, {"collection_id": "OTHER"}, {"type": "idea", "untagged": "true"}],
)
def test_cursor_with_different_filters_is_rejected(client, store, inbox, other_filters):
    other = make_collection(client, "Other")
    for minutes in range(3):
        add_note(client, store, inbox, minutes)
    cursor = timeline(client, limit=1, type="idea")["next_cursor"]
    params = {k: (other if v == "OTHER" else v) for k, v in other_filters.items()}
    response = client.get("/timeline", params={"limit": 1, "cursor": cursor, **params})
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid cursor"}


def test_cursor_can_change_limit(client, store, inbox):
    created = [add_note(client, store, inbox, minutes) for minutes in range(5)]
    first = timeline(client, limit=1)
    second = timeline(client, limit=3, cursor=first["next_cursor"])
    assert ids(second) == [created[3], created[2], created[1]]


# --- Filters ------------------------------------------------------------------------------------


@pytest.fixture
def tree(client) -> dict[str, str]:
    """root > child > grandchild > great, plus a sibling of root's child and an unrelated root."""
    root = make_collection(client, "Root")
    child = make_collection(client, "Child", root)
    grandchild = make_collection(client, "Grandchild", child)
    great = make_collection(client, "Great", grandchild)
    sibling = make_collection(client, "Sibling", root)
    other = make_collection(client, "Other")
    return {
        "root": root,
        "child": child,
        "grandchild": grandchild,
        "great": great,
        "sibling": sibling,
        "other": other,
    }


def test_collection_filter_without_descendants(client, store, tree):
    in_child = add_note(client, store, tree["child"], 1)
    add_note(client, store, tree["grandchild"], 2)
    add_note(client, store, tree["root"], 3)
    assert ids(timeline(client, collection_id=tree["child"])) == [in_child]
    assert ids(timeline(client, collection_id=tree["child"], include_descendants="false")) == [in_child]


def test_collection_filter_with_descendants_three_levels_deep(client, store, tree):
    notes = {name: add_note(client, store, cid, minutes) for minutes, (name, cid) in enumerate(tree.items())}
    page = timeline(client, collection_id=tree["child"], include_descendants="true")
    assert ids(page) == [notes["great"], notes["grandchild"], notes["child"]]

    page = timeline(client, collection_id=tree["root"], include_descendants="true")
    expected = [notes[name] for name in ("sibling", "great", "grandchild", "child", "root")]
    assert ids(page) == expected


def test_descendants_without_collection_is_rejected(client):
    response = client.get("/timeline", params={"include_descendants": "true"})
    assert response.status_code == 422


def test_unknown_collection_is_rejected(client):
    response = client.get("/timeline", params={"collection_id": "no-such-collection"})
    assert response.status_code == 422
    assert response.json() == {"detail": "Collection not found"}


@pytest.mark.parametrize("type_", TYPES)
def test_type_filter(client, store, inbox, type_):
    created = {t: add_note(client, store, inbox, minutes, t) for minutes, t in enumerate(TYPES)}
    assert ids(timeline(client, type=type_)) == [created[type_]]


@pytest.mark.parametrize("value", ["task", "Memory", ""])
def test_bad_type_is_rejected(client, value):
    assert client.get("/timeline", params={"type": value}).status_code == 422


def test_tag_filter(client, store, inbox):
    a = make_tag(client, "a")
    b = make_tag(client, "b")
    tagged_a = add_note(client, store, inbox, 1, tag_ids=[a])
    tagged_ab = add_note(client, store, inbox, 2, tag_ids=[b, a])
    add_note(client, store, inbox, 3, tag_ids=[b])
    add_note(client, store, inbox, 4)
    assert ids(timeline(client, tag_id=a)) == [tagged_ab, tagged_a]


def test_unknown_tag_is_rejected(client):
    response = client.get("/timeline", params={"tag_id": "no-such-tag"})
    assert response.status_code == 422
    assert response.json() == {"detail": "Tag not found"}


def test_untagged_filter(client, store, inbox):
    tag = make_tag(client, "t")
    add_note(client, store, inbox, 1, tag_ids=[tag])
    untagged = add_note(client, store, inbox, 2)
    assert ids(timeline(client, untagged="true")) == [untagged]
    assert len(timeline(client, untagged="false")["items"]) == 2


def test_untagged_with_tag_is_rejected(client, inbox):
    tag = make_tag(client, "t")
    response = client.get("/timeline", params={"untagged": "true", "tag_id": tag})
    assert response.status_code == 422


def test_filters_combine(client, store, tree):
    tag = make_tag(client, "t")
    match = add_note(client, store, tree["grandchild"], 1, "plan", tag_ids=[tag])
    add_note(client, store, tree["grandchild"], 2, "plan")
    add_note(client, store, tree["grandchild"], 3, "idea", tag_ids=[tag])
    add_note(client, store, tree["other"], 4, "plan", tag_ids=[tag])
    page = timeline(
        client, collection_id=tree["root"], include_descendants="true", type="plan", tag_id=tag
    )
    assert ids(page) == [match]


def test_note_leaves_untagged_view_once_tagged_and_returns(client, store, inbox):
    tag = make_tag(client, "t")
    note_id = add_note(client, store, inbox, 1)
    assert ids(timeline(client, untagged="true")) == [note_id]
    assert ids(timeline(client, tag_id=tag)) == []

    assert patch_note(client, note_id, {"tag_ids": [tag]}).status_code == 200
    assert ids(timeline(client, untagged="true")) == []
    assert ids(timeline(client, tag_id=tag)) == [note_id]

    assert patch_note(client, note_id, {"tag_ids": []}).status_code == 200
    assert ids(timeline(client, untagged="true")) == [note_id]


def test_moved_note_follows_its_collection(client, store, tree):
    note_id = add_note(client, store, tree["child"], 1)
    assert patch_note(client, note_id, {"collection_id": tree["other"]}).status_code == 200
    assert ids(timeline(client, collection_id=tree["child"])) == []
    assert ids(timeline(client, collection_id=tree["other"])) == [note_id]


def test_pagination_with_filters(client, store, inbox):
    plans = [add_note(client, store, inbox, minutes * 2, "plan") for minutes in range(5)]
    for minutes in range(5):
        add_note(client, store, inbox, minutes * 2 + 1, "idea")
    first = timeline(client, type="plan", limit=2)
    assert ids(first) == [plans[4], plans[3]]
    assert all_ids(client, type="plan", limit=2) == list(reversed(plans))


def test_timeline_changes_nothing(client, store, inbox):
    tag = make_tag(client, "t")
    for minutes in range(3):
        add_note(client, store, inbox, minutes, "memory", tag_ids=[tag])
    before = sorted((n.model_dump() for n in store.notes.list()), key=lambda n: n["id"])
    all_ids(client, limit=1)
    timeline(client, tag_id=tag)
    after = sorted((n.model_dump() for n in store.notes.list()), key=lambda n: n["id"])
    assert after == before

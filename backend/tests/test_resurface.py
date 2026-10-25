"""Tests for resurfacing (#16): `GET /resurface` and `POST /notes/{id}/resurfaced`."""

import random
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import app.main as app_main
from app.dependencies import get_clock, get_random
from tests.note_helpers import TYPES, create_note, get_note, make_collection
from tests.error_helpers import error_body

START = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


@pytest.fixture
def clock(app) -> FakeClock:
    fake = FakeClock(START)
    app.dependency_overrides[get_clock] = lambda: fake
    return fake


@pytest.fixture
def rng(app) -> random.Random:
    """One seeded generator shared by all requests, so repeated calls draw different numbers."""
    generator = random.Random(1234)
    app.dependency_overrides[get_random] = lambda: generator
    return generator


@pytest.fixture
def inbox(client) -> str:
    return make_collection(client, "Inbox")


def resurface(client, exclude: list[str] | None = None) -> list[dict]:
    response = client.get("/resurface", params={"exclude": exclude} if exclude else None)
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"items"}
    return response.json()["items"]


def ids(items: list[dict]) -> list[str]:
    return [item["id"] for item in items]


def mark(client, note_id: str) -> dict:
    response = client.post(f"/notes/{note_id}/resurfaced")
    assert response.status_code == 200, response.text
    return response.json()


def old_notes(client, clock: FakeClock, inbox: str, types: list[str]) -> list[str]:
    """Create notes at the current fake time, then move the clock 30 days on so they are eligible."""
    created = [create_note(client, inbox, type_)["id"] for type_ in types]
    clock.advance(timedelta(days=30))
    return created


# --- GET /resurface: eligibility ----------------------------------------------------------------


def test_no_notes(client, clock, rng):
    assert resurface(client) == []


def test_only_recent_notes(client, clock, rng, inbox):
    for type_ in TYPES:
        create_note(client, inbox, type_)
    clock.advance(timedelta(days=6, hours=23))
    assert resurface(client) == []


def test_seven_day_boundary(client, clock, rng, inbox):
    note_id = create_note(client, inbox, "idea")["id"]
    clock.advance(timedelta(days=7))
    assert resurface(client) == []
    clock.advance(timedelta(seconds=1))
    assert ids(resurface(client)) == [note_id]


def test_resurfaced_in_last_24h_is_never_returned(client, clock, rng, inbox):
    [shown, other] = old_notes(client, clock, inbox, ["memory", "idea"])
    mark(client, shown)
    clock.advance(timedelta(hours=23))
    for _ in range(50):
        assert ids(resurface(client)) == [other]
    clock.advance(timedelta(hours=2))
    assert set(ids(resurface(client))) == {shown, other}


def test_just_marked_note_is_not_returned(client, clock, rng, inbox):
    [note_id] = old_notes(client, clock, inbox, ["memory"])
    assert ids(resurface(client)) == [note_id]
    mark(client, note_id)
    assert resurface(client) == []


# --- GET /resurface: set size and Memory ---------------------------------------------------------


@pytest.mark.parametrize("count", [1, 2])
def test_few_eligible_notes_are_all_returned(client, clock, rng, inbox, count):
    created = old_notes(client, clock, inbox, ["idea"] * count)
    assert sorted(ids(resurface(client))) == sorted(created)


@pytest.mark.parametrize("count", [3, 4, 10])
def test_three_distinct_notes_when_enough_are_eligible(client, clock, rng, inbox, count):
    created = old_notes(client, clock, inbox, (TYPES * 2)[:count])
    for _ in range(30):
        picked = ids(resurface(client))
        assert len(picked) == 3
        assert len(set(picked)) == 3
        assert set(picked) <= set(created)


def test_always_contains_a_memory_when_one_is_eligible(client, clock, rng, inbox):
    [memory, *_] = old_notes(client, clock, inbox, ["memory", *["idea"] * 9])
    for _ in range(200):
        assert memory in ids(resurface(client))


def test_without_memories_still_returns_three(client, clock, rng, inbox):
    old_notes(client, clock, inbox, ["idea", "plan", "journal", "reference"])
    picked = resurface(client)
    assert len(picked) == 3
    assert all(item["type"] != "memory" for item in picked)


def test_items_match_get_note(client, clock, rng, inbox):
    old_notes(client, clock, inbox, TYPES)
    for item in resurface(client):
        assert item == get_note(client, item["id"])


# --- GET /resurface: exclude --------------------------------------------------------------------


def test_excluded_notes_are_avoided(client, clock, rng, inbox):
    created = old_notes(client, clock, inbox, ["memory", "idea", "idea", "memory", "idea", "idea"])
    excluded = created[:3]
    for _ in range(50):
        picked = ids(resurface(client, exclude=excluded))
        assert len(picked) == 3
        assert not set(picked) & set(excluded)


def test_excluded_notes_fill_up_when_too_few_others(client, clock, rng, inbox):
    created = old_notes(client, clock, inbox, ["idea", "idea", "idea", "idea"])
    for _ in range(50):
        picked = ids(resurface(client, exclude=created[:3]))
        assert len(picked) == 3
        assert len(set(picked)) == 3
        assert created[3] in picked


def test_fresh_memory_is_preferred_over_excluded_ones_when_filling(client, clock, rng, inbox):
    m1, i1, i2, m2 = old_notes(client, clock, inbox, ["memory", "idea", "idea", "memory"])
    for _ in range(200):
        picked = ids(resurface(client, exclude=[m1, i1, i2]))
        assert len(picked) == 3
        assert m2 in picked


def test_memory_rule_wins_when_only_excluded_notes_are_memories(client, clock, rng, inbox):
    created = old_notes(client, clock, inbox, ["memory", "idea", "idea", "idea", "idea"])
    memory, fresh = created[0], created[2:]
    for _ in range(50):
        picked = ids(resurface(client, exclude=created[:2]))
        assert memory in picked
        assert created[1] not in picked
        assert len(set(picked) & set(fresh)) == 2


def test_unknown_excluded_ids_are_ignored(client, clock, rng, inbox):
    created = old_notes(client, clock, inbox, ["idea", "memory"])
    assert sorted(ids(resurface(client, exclude=["nope", "also-nope"]))) == sorted(created)


# --- GET /resurface: weighting and determinism --------------------------------------------------


def test_never_resurfaced_note_is_picked_more_often(client, store, clock, rng, inbox):
    created = old_notes(client, clock, inbox, ["idea"] * 5)
    never, seen_two_days_ago = created[0], created[1]
    for note_id in created[1:]:
        stored = store.notes.get(note_id)
        store.notes.update(stored.model_copy(update={"last_resurfaced_at": clock.now - timedelta(days=2)}))
    counts: Counter[str] = Counter()
    for _ in range(1000):
        counts.update(ids(resurface(client)))
    assert counts[never] > counts[seen_two_days_ago]


def test_same_random_sequence_gives_same_result(app, client, clock, inbox):
    old_notes(client, clock, inbox, ["memory", "idea", "plan", "journal", "reference", "idea", "memory"])
    app.dependency_overrides[get_random] = lambda: random.Random(42)
    first = ids(resurface(client))
    for _ in range(10):
        assert ids(resurface(client)) == first


def test_get_changes_nothing(client, store, clock, rng, inbox):
    old_notes(client, clock, inbox, TYPES)
    before = sorted((n.model_dump() for n in store.notes.list()), key=lambda n: n["id"])
    for _ in range(5):
        resurface(client)
    after = sorted((n.model_dump() for n in store.notes.list()), key=lambda n: n["id"])
    assert after == before


# --- POST /notes/{id}/resurfaced ----------------------------------------------------------------


@pytest.mark.parametrize("type_", TYPES)
def test_mark_resurfaced(client, clock, rng, inbox, type_):
    created = create_note(client, inbox, type_)
    clock.advance(timedelta(days=10))
    marked = mark(client, created["id"])
    assert marked["resurface_count"] == 1
    assert datetime.fromisoformat(marked["last_resurfaced_at"]) == clock.now
    unchanged = {k: v for k, v in marked.items() if k not in ("resurface_count", "last_resurfaced_at")}
    assert unchanged == {k: v for k, v in created.items() if k not in ("resurface_count", "last_resurfaced_at")}
    assert get_note(client, created["id"]) == marked


def test_mark_twice(client, clock, rng, inbox):
    note_id = create_note(client, inbox, "memory")["id"]
    mark(client, note_id)
    clock.advance(timedelta(hours=3))
    second = mark(client, note_id)
    assert second["resurface_count"] == 2
    assert datetime.fromisoformat(second["last_resurfaced_at"]) == clock.now


def test_mark_unknown_note(client, clock, rng):
    response = client.post("/notes/no-such-note/resurfaced")
    assert response.status_code == 404
    assert response.json() == error_body("note_not_found", "Note not found")


def test_mark_ignores_body(client, clock, rng, inbox):
    note_id = create_note(client, inbox, "idea")["id"]
    response = client.post(
        f"/notes/{note_id}/resurfaced", json={"resurface_count": 99, "last_resurfaced_at": None}
    )
    assert response.status_code == 200
    assert response.json()["resurface_count"] == 1
    assert datetime.fromisoformat(response.json()["last_resurfaced_at"]) == clock.now


# --- Injection ----------------------------------------------------------------------------------


def test_resurfacing_code_does_not_use_global_random_or_clock():
    app_dir = Path(app_main.__file__).parent
    for path in (app_dir / "services" / "resurface.py", app_dir / "routers" / "resurface.py"):
        source = path.read_text(encoding="utf-8")
        assert "import random" not in source
        assert "datetime.now" not in source

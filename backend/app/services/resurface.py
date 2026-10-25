"""Resurfacing: pick a few older notes semi-randomly and record when a note was shown.

Mirrors the frontend's `resurface.ts`, plus a 24h cool-down after a note was shown.
"""

from collections.abc import Callable, Collection, Sequence
from datetime import datetime, timedelta
from typing import Protocol

from app.models.note import Note
from app.repositories.base import Repository
from app.services.errors import ServiceError

SET_SIZE = 3
MIN_AGE = timedelta(days=7)
COOLDOWN = timedelta(hours=24)
NEVER_RESURFACED_WEIGHT = 31.0
MAX_WEIGHT_DAYS = 30.0
_DAY_SECONDS = 24 * 60 * 60


class RandomSource(Protocol):
    def random(self) -> float: ...


class ResurfaceError(ServiceError):
    """Base class for resurfacing errors."""


class ResurfaceNoteNotFoundError(ResurfaceError):
    code = "note_not_found"
    message = "Note not found"


class ResurfaceService:
    def __init__(
        self,
        notes: Repository[Note],
        random: RandomSource,
        clock: Callable[[], datetime],
    ) -> None:
        self._notes = notes
        self._random = random
        self._clock = clock

    def pick(self, exclude: Collection[str] = ()) -> list[Note]:
        """Up to `SET_SIZE` distinct eligible notes, at least one Memory if any is eligible.

        Notes in `exclude` are only used when there aren't enough other eligible notes (to fill up)
        or when the only eligible Memories are excluded (the Memory rule wins).
        """
        now = self._clock()
        eligible = sorted(
            (note for note in self._notes.list() if self._is_eligible(note, now)),
            key=lambda note: (note.created_at, note.id),
        )
        target = min(SET_SIZE, len(eligible))
        fresh = [note for note in eligible if note.id not in exclude]
        picked: list[Note] = []

        def take(pool: Sequence[Note]) -> None:
            picked_ids = {note.id for note in picked}
            available = [note for note in pool if note.id not in picked_ids]
            if available and len(picked) < target:
                picked.append(self._weighted_pick(available, now))

        fresh_memories = [note for note in fresh if note.type == "memory"]
        take(fresh_memories or [note for note in eligible if note.type == "memory"])
        while len(picked) < target:
            before = len(picked)
            take(fresh)
            if len(picked) == before:
                take(eligible)
        return picked

    def mark_resurfaced(self, note_id: str) -> Note:
        note = self._notes.get(note_id)
        if note is None:
            raise ResurfaceNoteNotFoundError()
        shown = note.model_copy(
            update={"last_resurfaced_at": self._clock(), "resurface_count": note.resurface_count + 1}
        )
        stored = self._notes.update(shown)
        if stored is None:
            raise ResurfaceNoteNotFoundError()
        return stored

    @staticmethod
    def _is_eligible(note: Note, now: datetime) -> bool:
        if now - note.created_at <= MIN_AGE:
            return False
        return note.last_resurfaced_at is None or now - note.last_resurfaced_at > COOLDOWN

    @staticmethod
    def _weight(note: Note, now: datetime) -> float:
        """Never-resurfaced notes weigh most; the longer ago a note was shown, the more it weighs."""
        if note.last_resurfaced_at is None:
            return NEVER_RESURFACED_WEIGHT
        days = (now - note.last_resurfaced_at).total_seconds() / _DAY_SECONDS
        return 1 + min(MAX_WEIGHT_DAYS, max(0.0, days))

    def _weighted_pick(self, pool: Sequence[Note], now: datetime) -> Note:
        weights = [self._weight(note, now) for note in pool]
        remaining = self._random.random() * sum(weights)
        for note, weight in zip(pool, weights, strict=True):
            remaining -= weight
            if remaining < 0:
                return note
        return pool[-1]

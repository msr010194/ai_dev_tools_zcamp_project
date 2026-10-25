"""HTTP endpoints for resurfacing. Service errors are handled by `app.errors`."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_resurface_service
from app.errors import error_responses
from app.schemas.notes import NoteOut, NoteOutBase, to_note_out
from app.schemas.resurface import ResurfaceOut
from app.services.resurface import ResurfaceService

router = APIRouter(tags=["resurfacing"])

Service = Annotated[ResurfaceService, Depends(get_resurface_service)]


@router.get(
    "/resurface",
    response_model=ResurfaceOut,
    operation_id="getResurfacedNotes",
    summary="Pick up to three older notes to revisit",
    responses=error_responses(422),
)
def get_resurfaced_notes(
    service: Service,
    exclude: Annotated[
        list[str] | None,
        Query(description="Note ids to avoid, e.g. the previously shown set. Repeatable."),
    ] = None,
) -> dict[str, Any]:
    notes = service.pick(frozenset(exclude or ()))
    return {"items": [to_note_out(note) for note in notes]}


@router.post(
    "/notes/{note_id}/resurfaced",
    response_model=NoteOut,
    operation_id="markNoteResurfaced",
    summary="Record that a note was shown",
    responses=error_responses(404, 422),
)
def mark_note_resurfaced(note_id: str, service: Service) -> NoteOutBase:
    return to_note_out(service.mark_resurfaced(note_id))

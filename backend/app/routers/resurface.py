"""HTTP endpoints for resurfacing; service errors become `{"detail": message}` responses."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_resurface_service
from app.schemas.notes import NoteOut, NoteOutBase, to_note_out
from app.schemas.resurface import ResurfaceOut
from app.services.resurface import ResurfaceError, ResurfaceService

router = APIRouter(tags=["resurfacing"])

Service = Annotated[ResurfaceService, Depends(get_resurface_service)]


@router.get(
    "/resurface",
    response_model=ResurfaceOut,
    operation_id="getResurfacedNotes",
    summary="Pick up to three older notes to revisit",
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
)
def mark_note_resurfaced(note_id: str, service: Service) -> NoteOutBase:
    try:
        note = service.mark_resurfaced(note_id)
    except ResurfaceError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return to_note_out(note)

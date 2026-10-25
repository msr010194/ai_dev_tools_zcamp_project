"""HTTP endpoints for notes. Service errors are turned into error responses by `app.errors`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_note_service
from app.errors import error_responses
from app.schemas.notes import (
    SHARED_CREATE_FIELDS,
    NoteCreate,
    NoteOut,
    NoteOutBase,
    NoteUpdate,
    to_note_out,
)
from app.services.notes import NoteService

router = APIRouter(prefix="/notes", tags=["notes"])

Service = Annotated[NoteService, Depends(get_note_service)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=NoteOut,
    operation_id="createNote",
    summary="Create a note",
    responses=error_responses(422),
)
def create_note(payload: NoteCreate, service: Service) -> NoteOutBase:
    fields = payload.model_dump(exclude_unset=True, exclude=set(SHARED_CREATE_FIELDS))
    note = service.create(payload.type, payload.body, payload.collection_id, payload.tag_ids, fields)
    return to_note_out(note)


@router.get(
    "/{note_id}",
    response_model=NoteOut,
    operation_id="getNote",
    summary="Get a note",
    responses=error_responses(404, 422),
)
def get_note(note_id: str, service: Service) -> NoteOutBase:
    return to_note_out(service.get(note_id))


@router.patch(
    "/{note_id}",
    response_model=NoteOut,
    operation_id="updateNote",
    summary="Update part of a note",
    responses=error_responses(404, 422),
)
def update_note(note_id: str, payload: NoteUpdate, service: Service) -> NoteOutBase:
    changes = payload.model_dump(include=payload.model_fields_set)
    return to_note_out(service.update(note_id, changes))


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    operation_id="deleteNote",
    summary="Delete a note",
    responses=error_responses(404, 422),
)
def delete_note(note_id: str, service: Service) -> Response:
    service.delete(note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

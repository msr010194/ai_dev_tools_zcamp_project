"""HTTP endpoints for notes; service errors become `{"detail": message}` responses."""

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies import get_note_service
from app.schemas.notes import (
    SHARED_CREATE_FIELDS,
    NoteCreate,
    NoteOut,
    NoteOutBase,
    NoteUpdate,
    to_note_out,
)
from app.services.notes import (
    DuplicateTagIdError,
    EmptyNoteUpdateError,
    FieldNotAllowedError,
    NoteCollectionNotFoundError,
    NoteError,
    NoteNotFoundError,
    NoteService,
    NoteTagNotFoundError,
    NoteTypeChangeError,
    PeriodRequiresRetrospectiveError,
    PromptLockedError,
)

router = APIRouter(prefix="/notes", tags=["notes"])

Service = Annotated[NoteService, Depends(get_note_service)]

_STATUS_FOR_ERROR: dict[type[NoteError], int] = {
    NoteNotFoundError: status.HTTP_404_NOT_FOUND,
    NoteCollectionNotFoundError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    NoteTagNotFoundError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    DuplicateTagIdError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    NoteTypeChangeError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    EmptyNoteUpdateError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    FieldNotAllowedError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    PromptLockedError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    PeriodRequiresRetrospectiveError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _raise_http(error: NoteError) -> NoReturn:
    raise HTTPException(status_code=_STATUS_FOR_ERROR[type(error)], detail=str(error)) from error


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=NoteOut,
    operation_id="createNote",
    summary="Create a note",
)
def create_note(payload: NoteCreate, service: Service) -> NoteOutBase:
    fields = payload.model_dump(exclude_unset=True, exclude=set(SHARED_CREATE_FIELDS))
    try:
        note = service.create(
            payload.type, payload.body, payload.collection_id, payload.tag_ids, fields
        )
    except NoteError as error:
        _raise_http(error)
    return to_note_out(note)


@router.get("/{note_id}", response_model=NoteOut, operation_id="getNote", summary="Get a note")
def get_note(note_id: str, service: Service) -> NoteOutBase:
    try:
        note = service.get(note_id)
    except NoteError as error:
        _raise_http(error)
    return to_note_out(note)


@router.patch(
    "/{note_id}", response_model=NoteOut, operation_id="updateNote", summary="Update part of a note"
)
def update_note(note_id: str, payload: NoteUpdate, service: Service) -> NoteOutBase:
    changes = payload.model_dump(include=payload.model_fields_set)
    try:
        note = service.update(note_id, changes)
    except NoteError as error:
        _raise_http(error)
    return to_note_out(note)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    operation_id="deleteNote",
    summary="Delete a note",
)
def delete_note(note_id: str, service: Service) -> Response:
    try:
        service.delete(note_id)
    except NoteError as error:
        _raise_http(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

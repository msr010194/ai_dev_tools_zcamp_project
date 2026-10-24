"""HTTP endpoints for notes; service errors become `{"detail": message}` responses."""

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies import get_note_service
from app.schemas.notes import NoteCreate, NoteOut, NoteOutBase, NoteUpdate, to_note_out
from app.services.notes import (
    DuplicateTagIdError,
    EmptyNoteUpdateError,
    NoteCollectionNotFoundError,
    NoteError,
    NoteNotFoundError,
    NoteService,
    NoteTagNotFoundError,
    NoteTypeChangeError,
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
}


def _raise_http(error: NoteError) -> NoReturn:
    raise HTTPException(status_code=_STATUS_FOR_ERROR[type(error)], detail=str(error)) from error


@router.post("", status_code=status.HTTP_201_CREATED, response_model=NoteOut)
def create_note(payload: NoteCreate, service: Service) -> NoteOutBase:
    try:
        note = service.create(payload.type, payload.body, payload.collection_id, payload.tag_ids)
    except NoteError as error:
        _raise_http(error)
    return to_note_out(note)


@router.get("/{note_id}", response_model=NoteOut)
def get_note(note_id: str, service: Service) -> NoteOutBase:
    try:
        note = service.get(note_id)
    except NoteError as error:
        _raise_http(error)
    return to_note_out(note)


@router.patch("/{note_id}", response_model=NoteOut)
def update_note(note_id: str, payload: NoteUpdate, service: Service) -> NoteOutBase:
    changes = {name: getattr(payload, name) for name in payload.model_fields_set}
    try:
        note = service.update(note_id, changes)
    except NoteError as error:
        _raise_http(error)
    return to_note_out(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_note(note_id: str, service: Service) -> Response:
    try:
        service.delete(note_id)
    except NoteError as error:
        _raise_http(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

"""Tags API: parses requests, calls `TagService` and maps its errors to HTTP."""

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_tag_service
from app.schemas.tags import TagCreate, TagOut, TagUpdate
from app.services.tags import DuplicateTagNameError, TagError, TagNotFoundError, TagService

router = APIRouter(prefix="/tags", tags=["tags"])

Service = Annotated[TagService, Depends(get_tag_service)]

_STATUS_FOR_ERROR: dict[type[TagError], int] = {
    TagNotFoundError: status.HTTP_404_NOT_FOUND,
    DuplicateTagNameError: status.HTTP_409_CONFLICT,
}


def _raise_http(error: TagError) -> NoReturn:
    raise HTTPException(status_code=_STATUS_FOR_ERROR[type(error)], detail=str(error)) from error


@router.get("", response_model=list[TagOut], operation_id="listTags", summary="List tags")
def list_tags(service: Service) -> list[TagOut]:
    return [TagOut.model_validate(tag.model_dump()) for tag in service.list_tags()]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TagOut,
    operation_id="createTag",
    summary="Create a tag",
)
def create_tag(body: TagCreate, service: Service) -> TagOut:
    try:
        tag = service.create(body.name)
    except TagError as error:
        _raise_http(error)
    return TagOut.model_validate(tag.model_dump())


@router.patch("/{tag_id}", response_model=TagOut, operation_id="renameTag", summary="Rename a tag")
def rename_tag(tag_id: str, body: TagUpdate, service: Service) -> TagOut:
    try:
        tag = service.rename(tag_id, body.name)
    except TagError as error:
        _raise_http(error)
    return TagOut.model_validate(tag.model_dump())

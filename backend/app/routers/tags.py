"""Tags API: parses requests and calls `TagService`. Service errors are handled by `app.errors`."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import get_tag_service
from app.errors import error_responses
from app.schemas.tags import TagCreate, TagOut, TagUpdate
from app.services.tags import TagService

router = APIRouter(prefix="/tags", tags=["tags"])

Service = Annotated[TagService, Depends(get_tag_service)]


@router.get("", response_model=list[TagOut], operation_id="listTags", summary="List tags")
def list_tags(service: Service) -> list[TagOut]:
    return [TagOut.model_validate(tag.model_dump()) for tag in service.list_tags()]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TagOut,
    operation_id="createTag",
    summary="Create a tag",
    responses=error_responses(409, 422),
)
def create_tag(body: TagCreate, service: Service) -> TagOut:
    return TagOut.model_validate(service.create(body.name).model_dump())


@router.patch(
    "/{tag_id}",
    response_model=TagOut,
    operation_id="renameTag",
    summary="Rename a tag",
    responses=error_responses(404, 409, 422),
)
def rename_tag(tag_id: str, body: TagUpdate, service: Service) -> TagOut:
    return TagOut.model_validate(service.rename(tag_id, body.name).model_dump())

"""Collections API: parses requests and calls `CollectionService`. Service errors are handled by `app.errors`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_collection_service
from app.errors import error_responses
from app.schemas.collections import (
    CollectionCreate,
    CollectionOut,
    CollectionTreeNode,
    CollectionUpdate,
    dump_tree_json,
)
from app.services.collections import CollectionService

router = APIRouter(prefix="/collections", tags=["collections"])

Service = Annotated[CollectionService, Depends(get_collection_service)]


@router.get(
    "",
    response_model=list[CollectionTreeNode],
    operation_id="listCollections",
    summary="List collections as a tree",
)
def list_collections(service: Service) -> Response:
    """Return all collections as a tree; siblings are sorted by name, case-insensitively."""
    # Encoded directly: Pydantic's recursive serializer fails on deep trees.
    return Response(content=dump_tree_json(service.list_tree()), media_type="application/json")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CollectionOut,
    operation_id="createCollection",
    summary="Create a collection",
    responses=error_responses(409, 422),
)
def create_collection(body: CollectionCreate, service: Service) -> CollectionOut:
    collection = service.create(body.name, body.parent_id)
    return CollectionOut.model_validate(collection.model_dump())


@router.patch(
    "/{collection_id}",
    response_model=CollectionOut,
    operation_id="updateCollection",
    summary="Rename or move a collection",
    responses=error_responses(400, 404, 409, 422),
)
def update_collection(
    collection_id: str, body: CollectionUpdate, service: Service
) -> CollectionOut:
    """Rename and/or move a collection. Omit `parent_id` to stay put; `null` moves to top level."""
    collection = service.update(
        collection_id, name=body.name, move=body.moves, parent_id=body.parent_id
    )
    return CollectionOut.model_validate(collection.model_dump())


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    operation_id="deleteCollection",
    summary="Delete an empty collection",
    description=(
        "Delete an empty collection. A collection that still has child collections or notes "
        "is not deleted: the request is rejected with 409 Conflict. Unknown ids return 404."
    ),
    responses=error_responses(404, 409, 422),
)
def delete_collection(collection_id: str, service: Service) -> Response:
    service.delete(collection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

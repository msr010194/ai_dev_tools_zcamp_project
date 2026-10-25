"""HTTP endpoint for the unified timeline; service errors become `{"detail": message}` responses."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_timeline_service
from app.models.note import NoteType
from app.schemas.notes import to_note_out
from app.schemas.timeline import TimelinePageOut
from app.services.timeline import TimelineError, TimelineFilters, TimelineService

router = APIRouter(prefix="/timeline", tags=["timeline"])

Service = Annotated[TimelineService, Depends(get_timeline_service)]

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.get(
    "",
    response_model=TimelinePageOut,
    operation_id="getTimeline",
    summary="List notes newest first, one page at a time",
)
def get_timeline(
    service: Service,
    limit: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE, description="Page size, 1 to 100.")
    ] = DEFAULT_PAGE_SIZE,
    cursor: Annotated[
        str | None,
        Query(description="`next_cursor` from the previous page; only valid with the same filters."),
    ] = None,
    collection_id: Annotated[
        str | None, Query(description="Only notes in this collection.")
    ] = None,
    include_descendants: Annotated[
        bool,
        Query(description="With `collection_id`: also notes in all nested sub-collections."),
    ] = False,
    note_type: Annotated[
        NoteType | None, Query(alias="type", description="Only notes of this Type.")
    ] = None,
    tag_id: Annotated[str | None, Query(description="Only notes that have this tag.")] = None,
    untagged: Annotated[
        bool, Query(description="Only notes without tags; cannot be combined with `tag_id`.")
    ] = False,
) -> dict[str, Any]:
    filters = TimelineFilters(
        collection_id=collection_id,
        include_descendants=include_descendants,
        type=note_type,
        tag_id=tag_id,
        untagged=untagged,
    )
    try:
        page = service.page(filters, limit, cursor)
    except TimelineError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return {"items": [to_note_out(note) for note in page.items], "next_cursor": page.next_cursor}

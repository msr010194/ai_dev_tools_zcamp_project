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


@router.get("", response_model=TimelinePageOut)
def get_timeline(
    service: Service,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
    collection_id: str | None = None,
    include_descendants: bool = False,
    note_type: Annotated[NoteType | None, Query(alias="type")] = None,
    tag_id: str | None = None,
    untagged: bool = False,
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

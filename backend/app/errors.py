"""One error body for every failure: `{"code", "message", "errors"}`, plus the handlers that produce it."""

from collections.abc import Sequence
from typing import Any, Literal

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models.note import NOTE_CLASSES
from app.services import collections, notes, resurface, tags, timeline
from app.services.errors import ServiceError

ErrorLocation = Literal["body", "query", "path"]


class ErrorItem(BaseModel):
    """One invalid input: where it was (`location`), which field (`field`, dot-joined) and why."""

    location: ErrorLocation
    field: str | None
    message: str


class Error(BaseModel):
    """The body of every error response. `errors` is non-empty only for `validation_error`."""

    code: str
    message: str
    errors: list[ErrorItem]


STATUS_FOR_ERROR: dict[type[ServiceError], int] = {
    collections.CollectionNotFoundError: status.HTTP_404_NOT_FOUND,
    collections.ParentCollectionNotFoundError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    collections.CollectionCycleError: status.HTTP_400_BAD_REQUEST,
    collections.DuplicateCollectionNameError: status.HTTP_409_CONFLICT,
    collections.CollectionNotEmptyError: status.HTTP_409_CONFLICT,
    tags.TagNotFoundError: status.HTTP_404_NOT_FOUND,
    tags.DuplicateTagNameError: status.HTTP_409_CONFLICT,
    notes.NoteNotFoundError: status.HTTP_404_NOT_FOUND,
    notes.NoteCollectionNotFoundError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    notes.NoteTagNotFoundError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    notes.DuplicateTagIdError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    notes.NoteTypeChangeError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    notes.EmptyNoteUpdateError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    notes.FieldNotAllowedError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    notes.PromptLockedError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    notes.PeriodRequiresRetrospectiveError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    timeline.InvalidCursorError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    timeline.TimelineCollectionNotFoundError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    timeline.TimelineTagNotFoundError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    timeline.DescendantsWithoutCollectionError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    timeline.UntaggedWithTagError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    resurface.ResurfaceNoteNotFoundError: status.HTTP_404_NOT_FOUND,
}

_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    status.HTTP_404_NOT_FOUND: ("not_found", "Not found"),
    status.HTTP_405_METHOD_NOT_ALLOWED: ("method_not_allowed", "Method not allowed"),
}
_RESPONSE_DESCRIPTIONS = {
    status.HTTP_400_BAD_REQUEST: "The request breaks a rule (e.g. a collection cycle)",
    status.HTTP_404_NOT_FOUND: "Not found",
    status.HTTP_409_CONFLICT: "Conflicts with existing data",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "Invalid input (`validation_error`) or a broken business rule",
}
_NOTE_TYPES = frozenset(NOTE_CLASSES)
_TAG_ERRORS = {"union_tag_invalid", "union_tag_not_found"}
_VALUE_ERROR_PREFIX = "Value error, "


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` entries declaring the `Error` body for the given statuses."""
    return {code: {"model": Error, "description": _RESPONSE_DESCRIPTIONS[code]} for code in statuses}


def _body(code: str, message: str, errors: Sequence[ErrorItem] = ()) -> dict[str, Any]:
    return Error(code=code, message=message, errors=list(errors)).model_dump()


def _error_item(error: dict[str, Any]) -> ErrorItem:
    location, *path = error["loc"] or ["body"]
    if location not in ("body", "query", "path"):
        location, path = "body", [location, *path]
    # A note body is a union tagged by `type`; Pydantic puts the tag in the path (`journal.mood`).
    if location == "body" and path and path[0] in _NOTE_TYPES:
        path = path[1:]
    if error["type"] in _TAG_ERRORS:
        path = ["type"]
    if error["type"] == "json_invalid":
        path = []
    message = str(error["msg"]).removeprefix(_VALUE_ERROR_PREFIX)
    field = ".".join(str(part) for part in path) or None
    return ErrorItem(location=location, field=field, message=message)


async def _service_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, ServiceError)
    return JSONResponse(
        _body(error.code, error.message), status_code=STATUS_FOR_ERROR[type(error)]
    )


async def _validation_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    items = [_error_item(item) for item in error.errors()]
    return JSONResponse(
        _body("validation_error", "The request is invalid", items),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


async def _http_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, StarletteHTTPException)
    code, message = _HTTP_ERRORS.get(error.status_code, (f"http_{error.status_code}", str(error.detail)))
    return JSONResponse(
        _body(code, message), status_code=error.status_code, headers=error.headers
    )


async def _unhandled_error(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(
        _body("internal_error", "Internal server error"),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, _service_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unhandled_error)

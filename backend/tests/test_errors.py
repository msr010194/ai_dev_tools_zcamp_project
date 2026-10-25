"""Tests for the uniform error body (#18): `{"code", "message", "errors"}` for every failure."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_note_service
from app.errors import STATUS_FOR_ERROR
from app.main import create_app
from app.services.errors import ServiceError
from tests.error_helpers import assert_validation_error, error_body
from tests.note_helpers import create_note, make_collection, make_tag

ERROR_SCHEMA = {"$ref": "#/components/schemas/Error"}
DECLARED_ERRORS = {
    "createCollection": {409, 422},
    "updateCollection": {400, 404, 409, 422},
    "deleteCollection": {404, 409},
    "createTag": {409, 422},
    "renameTag": {404, 409, 422},
    "createNote": {422},
    "getNote": {404},
    "updateNote": {404, 422},
    "deleteNote": {404},
    "getTimeline": {422},
    "markNoteResurfaced": {404},
}


@pytest.fixture
def world(client) -> dict[str, str]:
    root = make_collection(client, "Root")
    child = make_collection(client, "Child", root)
    tag = make_tag(client, "work")
    journal = create_note(client, child, "journal", prompt="Fixed")
    return {"root": root, "child": child, "tag": tag, "journal": journal["id"]}


Case = Callable[[TestClient, dict[str, str]], Any]

CASES: dict[str, tuple[int, str, Case]] = {
    # 400
    "collection_cycle": (
        400,
        "collection_cycle",
        lambda c, w: c.patch(f"/collections/{w['root']}", json={"parent_id": w["child"]}),
    ),
    # 404 unknown ids
    "collection_404": (
        404,
        "collection_not_found",
        lambda c, w: c.patch("/collections/missing", json={"name": "x"}),
    ),
    "tag_404": (404, "tag_not_found", lambda c, w: c.patch("/tags/missing", json={"name": "x"})),
    "note_404": (404, "note_not_found", lambda c, w: c.get("/notes/missing")),
    "resurfaced_404": (404, "note_not_found", lambda c, w: c.post("/notes/missing/resurfaced")),
    # 404 / 405 routing
    "unknown_route": (404, "not_found", lambda c, w: c.get("/does-not-exist")),
    "wrong_method": (405, "method_not_allowed", lambda c, w: c.delete("/tags")),
    # 409
    "duplicate_collection_name": (
        409,
        "duplicate_collection_name",
        lambda c, w: c.post("/collections", json={"name": "root"}),
    ),
    "collection_not_empty": (409, "collection_not_empty", lambda c, w: c.delete(f"/collections/{w['root']}")),
    "duplicate_tag_name": (409, "duplicate_tag_name", lambda c, w: c.post("/tags", json={"name": "Work"})),
    # 422 validation
    "validation_error": (422, "validation_error", lambda c, w: c.post("/tags", json={})),
    # 422 business rules
    "parent_collection_not_found": (
        422,
        "parent_collection_not_found",
        lambda c, w: c.post("/collections", json={"name": "x", "parent_id": "missing"}),
    ),
    "note_collection_not_found": (
        422,
        "collection_not_found",
        lambda c, w: c.post("/notes", json={"type": "idea", "body": "x", "collection_id": "missing"}),
    ),
    "note_tag_not_found": (
        422,
        "tag_not_found",
        lambda c, w: c.post(
            "/notes", json={"type": "idea", "body": "x", "collection_id": w["root"], "tag_ids": ["missing"]}
        ),
    ),
    "duplicate_tag_id": (
        422,
        "duplicate_tag_id",
        lambda c, w: c.patch(f"/notes/{w['journal']}", json={"tag_ids": [w["tag"], w["tag"]]}),
    ),
    "note_type_change": (
        422,
        "note_type_change",
        lambda c, w: c.patch(f"/notes/{w['journal']}", json={"type": "idea"}),
    ),
    "empty_update": (422, "empty_update", lambda c, w: c.patch(f"/notes/{w['journal']}", json={})),
    "field_not_allowed": (
        422,
        "field_not_allowed",
        lambda c, w: c.patch(f"/notes/{w['journal']}", json={"link": "https://example.com"}),
    ),
    "prompt_locked": (
        422,
        "prompt_locked",
        lambda c, w: c.patch(f"/notes/{w['journal']}", json={"prompt": "Other"}),
    ),
    "period_requires_retrospective": (
        422,
        "period_requires_retrospective",
        lambda c, w: c.patch(f"/notes/{w['journal']}", json={"period": "weekly"}),
    ),
    "invalid_cursor": (422, "invalid_cursor", lambda c, w: c.get("/timeline", params={"cursor": "nope"})),
    "timeline_collection_not_found": (
        422,
        "collection_not_found",
        lambda c, w: c.get("/timeline", params={"collection_id": "missing"}),
    ),
    "timeline_tag_not_found": (
        422,
        "tag_not_found",
        lambda c, w: c.get("/timeline", params={"tag_id": "missing"}),
    ),
    "descendants_require_collection": (
        422,
        "descendants_require_collection",
        lambda c, w: c.get("/timeline", params={"include_descendants": "true"}),
    ),
    "untagged_with_tag": (
        422,
        "untagged_with_tag",
        lambda c, w: c.get("/timeline", params={"untagged": "true", "tag_id": w["tag"]}),
    ),
}


# --- Shape --------------------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_every_documented_error(client, world, case):
    status, code, call = CASES[case]
    response = call(client, world)
    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert set(body) == {"code", "message", "errors"}
    assert body["code"] == code
    assert isinstance(body["message"], str) and body["message"]
    assert (body["errors"] != []) == (code == "validation_error")


def test_400_collection_cycle_body(client, world):
    response = client.patch(f"/collections/{world['root']}", json={"parent_id": world["child"]})
    assert response.json() == error_body(
        "collection_cycle", "A collection cannot be moved under itself or one of its descendants"
    )


def test_404_note_body(client):
    assert client.get("/notes/missing").json() == error_body("note_not_found", "Note not found")


def test_404_route_and_405_method(client):
    assert client.get("/does-not-exist").json() == error_body("not_found", "Not found")
    response = client.delete("/tags")
    assert response.json() == error_body("method_not_allowed", "Method not allowed")
    assert "GET" in response.headers["allow"]


def test_409_duplicate_tag_body(client):
    make_tag(client, "work")
    response = client.post("/tags", json={"name": "Work"})
    assert response.json() == error_body("duplicate_tag_name", "A tag with that name already exists")


def test_422_business_rule_body(client, world):
    response = client.patch(f"/notes/{world['journal']}", json={"prompt": "Other"})
    assert response.json() == error_body("prompt_locked", "Prompt cannot be changed once set")


# --- Validation items ---------------------------------------------------------------------------


def test_blank_body(client, world):
    response = client.post("/notes", json={"type": "idea", "body": "   ", "collection_id": world["root"]})
    errors = assert_validation_error(response)
    assert response.json()["message"] == "The request is invalid"
    assert errors == [{"location": "body", "field": "body", "message": "must not be blank"}]


def test_nested_field_path(client, world):
    response = client.post(
        "/notes",
        json={"type": "plan", "body": "x", "collection_id": world["root"], "checklist": [{"text": ""}]},
    )
    [error] = assert_validation_error(response)
    assert (error["location"], error["field"]) == ("body", "checklist.0.text")


def test_type_segment_is_dropped(client, world):
    response = client.post(
        "/notes", json={"type": "journal", "body": "x", "collection_id": world["root"], "mood": ""}
    )
    [error] = assert_validation_error(response)
    assert error["field"] == "mood"


@pytest.mark.parametrize("path", ["/tags", "/collections", "/notes"])
def test_unknown_field(client, world, path):
    payload = {"name": "x", "colour": "red"}
    if path == "/notes":
        payload = {"type": "idea", "body": "x", "collection_id": world["root"], "colour": "red"}
    errors = assert_validation_error(client.post(path, json=payload))
    assert {"location": "body", "field": "colour"} in [
        {"location": e["location"], "field": e["field"]} for e in errors
    ]


@pytest.mark.parametrize("type_", [None, "task"])
def test_bad_note_type_points_at_type(client, world, type_):
    payload = {"body": "x", "collection_id": world["root"]}
    if type_ is not None:
        payload["type"] = type_
    [error] = assert_validation_error(client.post("/notes", json=payload))
    assert error["field"] == "type"


def test_query_validation(client):
    [error] = assert_validation_error(client.get("/timeline", params={"limit": 0}))
    assert (error["location"], error["field"]) == ("query", "limit")


def test_malformed_json(client):
    response = client.post("/notes", content=b"{not json", headers={"content-type": "application/json"})
    [error] = assert_validation_error(response)
    assert (error["location"], error["field"]) == ("body", None)


def test_model_level_error_has_no_field(client, world):
    [error] = assert_validation_error(client.patch(f"/collections/{world['root']}", json={}))
    assert (error["location"], error["field"]) == ("body", None)
    assert not error["message"].startswith("Value error")


# --- 500 ----------------------------------------------------------------------------------------


class _Exploding:
    def get(self, note_id: str) -> None:
        raise RuntimeError("secret database password in traceback")


def test_unhandled_exception_is_a_generic_500():
    app = create_app()
    app.dependency_overrides[get_note_service] = lambda: _Exploding()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/notes/anything")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/json"
    assert response.json() == error_body("internal_error", "Internal server error")
    assert "secret" not in response.text and "Traceback" not in response.text


# --- Every service error is mapped and nothing returns `detail` ---------------------------------


def _all_subclasses(cls: type) -> set[type]:
    found = set()
    for sub in cls.__subclasses__():
        found |= {sub} | _all_subclasses(sub)
    return found


def test_every_concrete_service_error_has_a_status_and_code():
    concrete = {cls for cls in _all_subclasses(ServiceError) if "code" in cls.__dict__}
    assert concrete == set(STATUS_FOR_ERROR)
    for cls in concrete:
        assert cls.code.islower() and " " not in cls.code


@pytest.mark.parametrize("case", CASES)
def test_no_response_has_detail(client, world, case):
    _, _, call = CASES[case]
    assert "detail" not in call(client, world).json()


# --- Contract -----------------------------------------------------------------------------------


def test_error_schemas_in_spec(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert set(schemas["Error"]["properties"]) == {"code", "message", "errors"}
    assert set(schemas["Error"]["required"]) == {"code", "message", "errors"}
    assert set(schemas["ErrorItem"]["properties"]) == {"location", "field", "message"}
    assert schemas["ErrorItem"]["properties"]["location"]["enum"] == ["body", "query", "path"]
    assert "HTTPValidationError" not in schemas
    assert "ValidationError" not in schemas


def test_operations_declare_their_errors(client):
    spec = client.get("/openapi.json").json()
    declared: dict[str, set[int]] = {}
    for item in spec["paths"].values():
        for operation in item.values():
            errors = {
                int(status): response["content"]["application/json"]["schema"]
                for status, response in operation["responses"].items()
                if not status.startswith("2")
            }
            assert all(schema == ERROR_SCHEMA for schema in errors.values()), operation["operationId"]
            declared[operation["operationId"]] = set(errors)
    for operation_id, required in DECLARED_ERRORS.items():
        assert required <= declared[operation_id], operation_id

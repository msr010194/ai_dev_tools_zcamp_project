"""Tests for the committed OpenAPI contract (#17): it is up to date and every operation is fully described."""

import json
import tomllib
from pathlib import Path
from typing import Any

import pytest

from app.main import create_app
from scripts.export_openapi import EXPORT_COMMAND, SPEC_PATH, render_spec

BACKEND_DIR = Path(__file__).resolve().parents[1]
OPERATIONS = {
    ("get", "/health"): ("getHealth", "health"),
    ("get", "/collections"): ("listCollections", "collections"),
    ("post", "/collections"): ("createCollection", "collections"),
    ("patch", "/collections/{collection_id}"): ("updateCollection", "collections"),
    ("delete", "/collections/{collection_id}"): ("deleteCollection", "collections"),
    ("get", "/tags"): ("listTags", "tags"),
    ("post", "/tags"): ("createTag", "tags"),
    ("patch", "/tags/{tag_id}"): ("renameTag", "tags"),
    ("post", "/notes"): ("createNote", "notes"),
    ("get", "/notes/{note_id}"): ("getNote", "notes"),
    ("patch", "/notes/{note_id}"): ("updateNote", "notes"),
    ("delete", "/notes/{note_id}"): ("deleteNote", "notes"),
    ("get", "/timeline"): ("getTimeline", "timeline"),
    ("get", "/resurface"): ("getResurfacedNotes", "resurfacing"),
    ("post", "/notes/{note_id}/resurfaced"): ("markNoteResurfaced", "resurfacing"),
}
NO_CONTENT_OPERATIONS = {"deleteCollection", "deleteNote"}
SCHEMA_KEYWORDS = {"type", "$ref", "oneOf", "anyOf", "allOf", "enum", "const"}


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    return create_app().openapi()


def operations(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        (method, path, operation)
        for path, item in spec["paths"].items()
        for method, operation in item.items()
    ]


def json_schema(content_holder: dict[str, Any]) -> dict[str, Any] | None:
    return content_holder.get("content", {}).get("application/json", {}).get("schema")


def is_named(schema: dict[str, Any]) -> bool:
    """A `$ref`, an array of `$ref`s, or a `oneOf` of `$ref`s."""
    if "$ref" in schema:
        return True
    if schema.get("type") == "array":
        return is_named(schema["items"])
    if "oneOf" in schema:
        return all("$ref" in option for option in schema["oneOf"])
    return False


def untyped_schemas(schema: Any, where: str) -> list[str]:
    """Paths of schemas that don't say what they contain (`{}`, bare objects, `additionalProperties: true`)."""
    if not isinstance(schema, dict):
        return []
    found = []
    if not SCHEMA_KEYWORDS & set(schema):
        found.append(where)
    if schema.get("additionalProperties") is True:
        found.append(f"{where}.additionalProperties")
    if schema.get("type") == "object" and "properties" not in schema and not isinstance(
        schema.get("additionalProperties"), dict
    ):
        found.append(where)
    for name, sub in schema.get("properties", {}).items():
        found += untyped_schemas(sub, f"{where}.{name}")
    for key in ("items", "additionalProperties"):
        found += untyped_schemas(schema.get(key), f"{where}.{key}")
    for key in ("oneOf", "anyOf", "allOf"):
        for index, sub in enumerate(schema.get(key, [])):
            found += untyped_schemas(sub, f"{where}.{key}[{index}]")
    return found


# --- Staleness ----------------------------------------------------------------------------------


def test_committed_spec_is_up_to_date(spec):
    assert SPEC_PATH.exists(), f"contract/openapi.json is missing. Run: {EXPORT_COMMAND}"
    committed = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assert committed == spec, f"contract/openapi.json is out of date. Run: {EXPORT_COMMAND}"


def test_rendering_is_deterministic(spec):
    assert render_spec(spec) == render_spec(create_app().openapi())
    assert render_spec(spec).endswith("}\n")


def test_info(spec):
    with (BACKEND_DIR / "pyproject.toml").open("rb") as file:
        version = tomllib.load(file)["project"]["version"]
    assert spec["info"] == {"title": "Notes API", "version": version}


# --- Operation metadata -------------------------------------------------------------------------


def test_exactly_the_documented_operations_ids_and_tags(spec):
    actual = {
        (method, path): (operation["operationId"], tuple(operation["tags"]))
        for method, path, operation in operations(spec)
    }
    assert actual == {key: (op_id, (tag,)) for key, (op_id, tag) in OPERATIONS.items()}


def test_every_operation_has_a_short_hand_written_summary(spec):
    for method, path, operation in operations(spec):
        summary = operation.get("summary", "")
        assert summary.strip(), f"{method} {path} has no summary"
        assert len(summary) <= 80, f"{method} {path} summary is too long"
        # FastAPI's automatic summary is the function name in Title Case.
        assert not summary.istitle(), f"{method} {path} summary looks auto-generated: {summary!r}"


@pytest.mark.parametrize("path", ["/timeline", "/resurface"])
def test_query_parameters_are_described(spec, path):
    parameters = spec["paths"][path]["get"]["parameters"]
    assert parameters
    for parameter in parameters:
        assert parameter["in"] == "query"
        assert parameter.get("description", "").strip(), f"{path} ?{parameter['name']} has no description"


def test_request_bodies_reference_named_schemas(spec):
    for method, path, operation in operations(spec):
        if "requestBody" in operation:
            schema = json_schema(operation["requestBody"])
            assert schema is not None and is_named(schema), f"{method} {path} request body is not named"


def test_success_responses_reference_named_schemas(spec):
    for method, path, operation in operations(spec):
        for status, response in operation["responses"].items():
            if not status.startswith("2"):
                continue
            schema = json_schema(response)
            if operation["operationId"] in NO_CONTENT_OPERATIONS:
                assert status == "204"
                assert "content" not in response, f"{method} {path} 204 declares content"
            else:
                assert schema is not None and is_named(schema), f"{method} {path} {status} is not named"


def test_no_untyped_schemas(spec):
    problems = []
    for name, schema in spec["components"]["schemas"].items():
        problems += untyped_schemas(schema, name)
    for method, path, operation in operations(spec):
        for holder in [operation.get("requestBody", {}), *operation["responses"].values()]:
            problems += untyped_schemas(json_schema(holder), f"{method} {path}")
    assert problems == []


def test_health_uses_named_schema(client, spec):
    schema = json_schema(spec["paths"]["/health"]["get"]["responses"]["200"])
    assert schema == {"$ref": "#/components/schemas/Health"}
    assert client.get("/health").json() == {"status": "ok"}

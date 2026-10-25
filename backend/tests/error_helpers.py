"""Expected error bodies (#18)."""

from typing import Any


def error_body(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message, "errors": []}


def assert_validation_error(response: Any) -> list[dict[str, Any]]:
    """Assert a 422 `validation_error` with at least one item, and return the items."""
    assert response.status_code == 422, response.text
    body = response.json()
    assert set(body) == {"code", "message", "errors"}
    assert body["code"] == "validation_error"
    assert body["errors"]
    for item in body["errors"]:
        assert set(item) == {"location", "field", "message"}
        assert item["location"] in ("body", "query", "path")
    return body["errors"]

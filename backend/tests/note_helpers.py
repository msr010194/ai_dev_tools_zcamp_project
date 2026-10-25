"""Small API helpers shared by the note test modules."""

from typing import Any

from fastapi.testclient import TestClient

TYPES = ["journal", "idea", "reference", "plan", "memory"]


def make_collection(client: TestClient, name: str = "Inbox", parent_id: str | None = None) -> str:
    payload: dict[str, Any] = {"name": name}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    response = client.post("/collections", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def make_tag(client: TestClient, name: str) -> str:
    response = client.post("/tags", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def note_payload(collection_id: str, type_: str = "journal", body: str = "Hello", **extra: Any) -> dict:
    return {"type": type_, "body": body, "collection_id": collection_id, **extra}


def create_note(client: TestClient, collection_id: str, type_: str = "journal", **extra: Any) -> dict:
    response = client.post("/notes", json=note_payload(collection_id, type_, **extra))
    assert response.status_code == 201, response.text
    return response.json()


def get_note(client: TestClient, note_id: str) -> dict:
    response = client.get(f"/notes/{note_id}")
    assert response.status_code == 200, response.text
    return response.json()


def patch_note(client: TestClient, note_id: str, payload: dict) -> Any:
    return client.patch(f"/notes/{note_id}", json=payload)

import pytest
from pydantic import BaseModel

from app.models.collection import Collection
from app.repositories.memory import InMemoryRepository

DUPLICATE = "A collection with that name already exists here"
NOT_FOUND = "Collection not found"
PARENT_NOT_FOUND = "Parent collection not found"
CYCLE = "A collection cannot be moved under itself or one of its descendants"
NOT_EMPTY = "Collection is not empty. Move or delete its contents first."


class FakeNote(BaseModel):
    id: str
    collection_id: str


def create(client, name, parent_id=None):
    body = {"name": name} if parent_id is None else {"name": name, "parent_id": parent_id}
    response = client.post("/collections", json=body)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def tree(client):
    response = client.get("/collections")
    assert response.status_code == 200
    return response.json()


def names(nodes):
    return [node["name"] for node in nodes]


def node(nodes, name):
    return next(n for n in nodes if n["name"] == name)


# List as a tree


def test_list_empty_returns_empty_list(client):
    response = client.get("/collections")
    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_nested_tree(client):
    work = create(client, "Work")
    project = create(client, "Project A", work)
    personal = create(client, "Personal")

    assert tree(client) == [
        {"id": personal, "name": "Personal", "parent_id": None, "children": []},
        {
            "id": work,
            "name": "Work",
            "parent_id": None,
            "children": [
                {"id": project, "name": "Project A", "parent_id": work, "children": []},
            ],
        },
    ]


def test_list_sorts_siblings_case_insensitively(client):
    for name in ("beta", "Alpha", "alpha 2"):
        create(client, name)
    parent = create(client, "Parent")
    for name in ("zeta", "Eta", "epsilon"):
        create(client, name, parent)

    nodes = tree(client)
    assert names(nodes) == ["Alpha", "alpha 2", "beta", "Parent"]
    assert names(node(nodes, "Parent")["children"]) == ["epsilon", "Eta", "zeta"]


def test_list_sorts_equal_names_by_id(client, store):
    # Equal folded names can only exist via the store, but the tie-break must still hold.
    for collection_id in ("c", "a", "b"):
        store.collections.add(Collection(id=collection_id, name="Same", parent_id=None))
    assert [n["id"] for n in tree(client)] == ["a", "b", "c"]


# Create


def test_create_top_level(client):
    response = client.post("/collections", json={"name": "Work"})
    assert response.status_code == 201
    body = response.json()
    assert body == {"id": body["id"], "name": "Work", "parent_id": None}
    assert isinstance(body["id"], str) and body["id"]
    assert tree(client) == [{"id": body["id"], "name": "Work", "parent_id": None, "children": []}]


def test_create_child(client):
    work = create(client, "Work")
    response = client.post("/collections", json={"name": "Project A", "parent_id": work})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Project A"
    assert body["parent_id"] == work
    assert tree(client)[0]["children"] == [
        {"id": body["id"], "name": "Project A", "parent_id": work, "children": []}
    ]


def test_create_trims_name(client):
    response = client.post("/collections", json={"name": "  Work  "})
    assert response.status_code == 201
    assert response.json()["name"] == "Work"
    assert names(tree(client)) == ["Work"]


def test_create_keeps_internal_whitespace(client):
    response = client.post("/collections", json={"name": " My   Work "})
    assert response.json()["name"] == "My   Work"


@pytest.mark.parametrize(
    ("body", "expected_status"),
    [
        pytest.param({"name": ""}, 422, id="empty"),
        pytest.param({"name": "   "}, 422, id="blank"),
        pytest.param({"name": "a" * 101}, 422, id="101-chars"),
        pytest.param({}, 422, id="missing"),
        pytest.param({"parent_id": None}, 422, id="missing-with-parent"),
        pytest.param({"name": None}, 422, id="null"),
        pytest.param({"name": 123}, 422, id="int"),
        pytest.param({"name": ["Work"]}, 422, id="list"),
        pytest.param({"name": "Work", "id": "my-id"}, 422, id="unknown-field-id"),
        pytest.param({"name": "Work", "children": []}, 422, id="unknown-field-children"),
        pytest.param({"name": "a" * 100}, 201, id="100-chars-accepted"),
        pytest.param({"name": "  " + "b" * 100 + "  "}, 201, id="100-chars-after-trim-accepted"),
    ],
)
def test_create_invalid_body_returns_422(client, body, expected_status):
    response = client.post("/collections", json=body)
    assert response.status_code == expected_status
    if expected_status == 422:
        assert isinstance(response.json()["detail"], list)
        assert tree(client) == []
    else:
        assert response.json()["name"] == body["name"].strip()
        assert names(tree(client)) == [body["name"].strip()]


def test_create_with_unknown_parent_returns_422(client):
    create(client, "Work")
    before = tree(client)
    response = client.post("/collections", json={"name": "Child", "parent_id": "missing"})
    assert response.status_code == 422
    assert response.json() == {"detail": PARENT_NOT_FOUND}
    assert tree(client) == before


def test_create_duplicate_sibling_name_returns_409(client):
    work = create(client, "Work")
    personal = create(client, "Personal")
    create(client, "Notes", work)
    before = tree(client)

    for name in ("work", "  WORK ", "Work"):
        response = client.post("/collections", json={"name": name})
        assert response.status_code == 409
        assert response.json() == {"detail": DUPLICATE}
    response = client.post("/collections", json={"name": "notes", "parent_id": work})
    assert response.status_code == 409
    assert response.json() == {"detail": DUPLICATE}
    assert tree(client) == before

    response = client.post("/collections", json={"name": "Work", "parent_id": personal})
    assert response.status_code == 201
    response = client.post("/collections", json={"name": "Work", "parent_id": work})
    assert response.status_code == 201


def test_create_generates_unique_ids(client):
    first_parent = create(client, "First")
    second_parent = create(client, "Second")
    first = create(client, "Same", first_parent)
    second = create(client, "Same", second_parent)
    assert first != second
    assert len({first_parent, second_parent, first, second}) == 4


# Rename and move


def test_patch_empty_body_returns_422(client):
    work = create(client, "Work")
    child = create(client, "Child", work)
    before = tree(client)

    response = client.patch(f"/collections/{child}", json={})
    assert response.status_code == 422
    assert tree(client) == before

    # Omitted parent_id: stays put; explicit null: moves to top level.
    assert client.patch(f"/collections/{child}", json={"name": "Renamed"}).json()["parent_id"] == work
    moved = client.patch(f"/collections/{child}", json={"parent_id": None})
    assert moved.status_code == 200
    assert moved.json() == {"id": child, "name": "Renamed", "parent_id": None}


def test_patch_rejects_invalid_bodies(client):
    work = create(client, "Work")
    before = tree(client)
    for body in (
        {"name": None},
        {"name": ""},
        {"name": "   "},
        {"name": "a" * 101},
        {"name": 5},
        {"id": "other"},
        {"name": "X", "children": []},
    ):
        response = client.patch(f"/collections/{work}", json=body)
        assert response.status_code == 422, body
        assert tree(client) == before


def test_rename_keeps_position_and_children(client):
    parent = create(client, "Parent")
    work = create(client, "Work", parent)
    child = create(client, "Child", work)

    response = client.patch(f"/collections/{work}", json={"name": "Personal"})
    assert response.status_code == 200
    assert response.json() == {"id": work, "name": "Personal", "parent_id": parent}
    assert tree(client) == [
        {
            "id": parent,
            "name": "Parent",
            "parent_id": None,
            "children": [
                {
                    "id": work,
                    "name": "Personal",
                    "parent_id": parent,
                    "children": [
                        {"id": child, "name": "Child", "parent_id": work, "children": []}
                    ],
                }
            ],
        }
    ]


def test_rename_validation_and_duplicates(client):
    work = create(client, "Work")
    create(client, "Personal")
    other_parent = create(client, "Other")
    create(client, "Work", other_parent)

    response = client.patch(f"/collections/{work}", json={"name": "  Job  "})
    assert response.status_code == 200
    assert response.json()["name"] == "Job"

    before = tree(client)
    for body in ({"name": ""}, {"name": "   "}, {"name": "a" * 101}, {"name": None}, {"name": 1}):
        response = client.patch(f"/collections/{work}", json=body)
        assert response.status_code == 422
        assert tree(client) == before

    for name in ("personal", "PERSONAL", " Personal "):
        response = client.patch(f"/collections/{work}", json={"name": name})
        assert response.status_code == 409
        assert response.json() == {"detail": DUPLICATE}
        assert tree(client) == before

    # A name used under a different parent is fine.
    assert client.patch(f"/collections/{work}", json={"name": "Work"}).status_code == 200
    # Renaming to its own name or a different case of it succeeds.
    response = client.patch(f"/collections/{work}", json={"name": "Work"})
    assert response.status_code == 200
    response = client.patch(f"/collections/{work}", json={"name": "WORK"})
    assert response.status_code == 200
    assert response.json() == {"id": work, "name": "WORK", "parent_id": None}

    response = client.patch(f"/collections/{work}", json={"name": "a" * 100})
    assert response.status_code == 200


def test_move_moves_whole_subtree(client):
    work = create(client, "Work")
    personal = create(client, "Personal")
    project = create(client, "Project A", work)
    sub = create(client, "Sub", project)
    leaf = create(client, "Leaf", sub)

    response = client.patch(f"/collections/{project}", json={"parent_id": personal})
    assert response.status_code == 200
    assert response.json() == {"id": project, "name": "Project A", "parent_id": personal}

    nodes = tree(client)
    assert node(nodes, "Work")["children"] == []
    assert node(nodes, "Personal")["children"] == [
        {
            "id": project,
            "name": "Project A",
            "parent_id": personal,
            "children": [
                {
                    "id": sub,
                    "name": "Sub",
                    "parent_id": project,
                    "children": [
                        {"id": leaf, "name": "Leaf", "parent_id": sub, "children": []}
                    ],
                }
            ],
        }
    ]


def test_move_to_top_level(client):
    work = create(client, "Work")
    project = create(client, "Project A", work)
    child = create(client, "Child", project)

    response = client.patch(f"/collections/{project}", json={"parent_id": None})
    assert response.status_code == 200
    assert response.json() == {"id": project, "name": "Project A", "parent_id": None}
    nodes = tree(client)
    assert names(nodes) == ["Project A", "Work"]
    assert node(nodes, "Project A")["children"][0]["id"] == child
    assert node(nodes, "Work")["children"] == []


def test_move_under_itself_returns_400(client):
    work = create(client, "Work")
    create(client, "Child", work)
    before = tree(client)

    response = client.patch(f"/collections/{work}", json={"parent_id": work})
    assert response.status_code == 400
    assert response.json() == {"detail": CYCLE}
    assert tree(client) == before


def test_move_under_descendant_returns_400(client):
    work = create(client, "Work")
    child = create(client, "Child", work)
    grandchild = create(client, "Grandchild", child)
    great = create(client, "Great", grandchild)
    before = tree(client)

    for target in (child, great):
        response = client.patch(f"/collections/{work}", json={"parent_id": target})
        assert response.status_code == 400
        assert response.json() == {"detail": CYCLE}
        assert tree(client) == before

    response = client.patch(f"/collections/{work}", json={"name": "Renamed", "parent_id": great})
    assert response.status_code == 400
    assert tree(client) == before


def test_move_under_unknown_parent_returns_422(client):
    work = create(client, "Work")
    create(client, "Child", work)
    before = tree(client)

    response = client.patch(f"/collections/{work}", json={"parent_id": "missing"})
    assert response.status_code == 422
    assert response.json() == {"detail": PARENT_NOT_FOUND}
    assert tree(client) == before


def test_move_into_duplicate_name_returns_409(client):
    work = create(client, "Work")
    personal = create(client, "Personal")
    create(client, "Ideas", personal)
    ideas = create(client, "IDEAS", work)
    before = tree(client)

    response = client.patch(f"/collections/{ideas}", json={"parent_id": personal})
    assert response.status_code == 409
    assert response.json() == {"detail": DUPLICATE}
    assert tree(client) == before

    # Moving to the top level where a "work" sibling exists is also a duplicate.
    nested_work = create(client, "work", personal)
    before = tree(client)
    response = client.patch(f"/collections/{nested_work}", json={"parent_id": None})
    assert response.status_code == 409
    assert tree(client) == before


def test_rename_and_move_together(client):
    work = create(client, "Work")
    personal = create(client, "Personal")
    create(client, "Taken", personal)
    project = create(client, "Project", work)
    create(client, "Renamed", work)

    # The new name is free under the new parent, even though it is taken under the old one.
    response = client.patch(
        f"/collections/{project}", json={"name": "Renamed", "parent_id": personal}
    )
    assert response.status_code == 200
    assert response.json() == {"id": project, "name": "Renamed", "parent_id": personal}
    assert names(node(tree(client), "Personal")["children"]) == ["Renamed", "Taken"]

    before = tree(client)
    # Duplicate under the new parent: neither name nor parent changes.
    response = client.patch(f"/collections/{project}", json={"name": "taken", "parent_id": personal})
    assert response.status_code == 409
    assert tree(client) == before
    response = client.patch(f"/collections/{project}", json={"name": "Work", "parent_id": None})
    assert response.status_code == 409
    assert tree(client) == before
    # Unknown parent: the rename is not applied either.
    response = client.patch(f"/collections/{project}", json={"name": "New", "parent_id": "missing"})
    assert response.status_code == 422
    assert tree(client) == before
    # Invalid name: the move is not applied either.
    response = client.patch(f"/collections/{project}", json={"name": "", "parent_id": None})
    assert response.status_code == 422
    assert tree(client) == before


def test_patch_unknown_id_returns_404(client):
    create(client, "Work")
    before = tree(client)
    for body in ({"name": "X"}, {"parent_id": None}):
        response = client.patch("/collections/does-not-exist", json=body)
        assert response.status_code == 404
        assert response.json() == {"detail": NOT_FOUND}
        assert tree(client) == before


# Delete


def test_delete_empty_collection(client):
    work = create(client, "Work")
    personal = create(client, "Personal")

    response = client.delete(f"/collections/{work}")
    assert response.status_code == 204
    assert response.content == b""
    assert [n["id"] for n in tree(client)] == [personal]


def test_delete_collection_with_children_returns_409(client):
    work = create(client, "Work")
    create(client, "Child", work)
    before = tree(client)

    response = client.delete(f"/collections/{work}")
    assert response.status_code == 409
    assert response.json() == {"detail": NOT_EMPTY}
    assert tree(client) == before


def test_delete_collection_with_notes_returns_409(client, store):
    work = create(client, "Work")
    store.notes.add(FakeNote(id="n1", collection_id=work))
    before = tree(client)

    response = client.delete(f"/collections/{work}")
    assert response.status_code == 409
    assert response.json() == {"detail": NOT_EMPTY}
    assert tree(client) == before
    assert store.collections.get(work) is not None


def test_delete_ignores_notes_in_other_collections(client, store):
    work = create(client, "Work")
    personal = create(client, "Personal")
    store.notes.add(FakeNote(id="n1", collection_id=personal))

    response = client.delete(f"/collections/{work}")
    assert response.status_code == 204
    assert [n["id"] for n in tree(client)] == [personal]


def test_delete_unknown_id_returns_404(client):
    create(client, "Work")
    before = tree(client)
    response = client.delete("/collections/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": NOT_FOUND}
    assert tree(client) == before


def test_delete_rule_is_documented_in_openapi(client):
    spec = client.get("/openapi.json").json()
    assert "409" in spec["paths"]["/collections/{collection_id}"]["delete"]["description"]


# Store and layering


def test_store_has_collections_and_empty_notes_repositories(store):
    assert isinstance(store.collections, InMemoryRepository)
    assert isinstance(store.notes, InMemoryRepository)
    assert store.collections.list() == []
    assert store.notes.list() == []


# Deep nesting


def test_deep_nesting_four_levels(client):
    work = create(client, "Work")
    project = create(client, "Project A", work)
    sub = create(client, "Subproject", project)
    detail = create(client, "Detail", sub)

    nodes = tree(client)
    assert names(nodes) == ["Work"]
    level2 = nodes[0]["children"]
    assert [(n["id"], n["parent_id"]) for n in level2] == [(project, work)]
    level3 = level2[0]["children"]
    assert [(n["id"], n["parent_id"]) for n in level3] == [(sub, project)]
    level4 = level3[0]["children"]
    assert level4 == [{"id": detail, "name": "Detail", "parent_id": sub, "children": []}]

    response = client.patch(f"/collections/{sub}", json={"parent_id": None})
    assert response.status_code == 200
    nodes = tree(client)
    assert names(nodes) == ["Subproject", "Work"]
    assert node(nodes, "Subproject")["children"] == [
        {"id": detail, "name": "Detail", "parent_id": sub, "children": []}
    ]
    assert node(nodes, "Work")["children"][0]["children"] == []

    # Put it back and try to create a cycle from the top.
    assert client.patch(f"/collections/{sub}", json={"parent_id": project}).status_code == 200
    before = tree(client)
    response = client.patch(f"/collections/{work}", json={"parent_id": detail})
    assert response.status_code == 400
    assert response.json() == {"detail": CYCLE}
    assert tree(client) == before

    for collection_id in (detail, sub, project, work):
        assert client.delete(f"/collections/{collection_id}").status_code == 204
    assert tree(client) == []


def test_deep_chain_created_through_api_lists_as_tree(client):
    depth = 300
    ids = []
    parent_id = None
    for level in range(depth):
        parent_id = create(client, f'Level "{level}" é', parent_id)
        ids.append(parent_id)

    nodes = tree(client)
    expected_parent = None
    for level, collection_id in enumerate(ids):
        assert len(nodes) == 1
        current = nodes[0]
        assert current["id"] == collection_id
        assert current["name"] == f'Level "{level}" é'
        assert current["parent_id"] == expected_parent
        expected_parent = collection_id
        nodes = current["children"]
    assert nodes == []

    before = tree(client)
    response = client.patch(f"/collections/{ids[0]}", json={"parent_id": ids[-1]})
    assert response.status_code == 400
    assert response.json() == {"detail": CYCLE}
    assert tree(client) == before


def test_very_deep_chain_lists_as_tree(client, store):
    # Deeper than Python's default recursion limit; the response is checked as text
    # because json.loads itself is recursive and cannot parse it.
    depth = 2000
    ids = [f"c{level:04d}" for level in range(depth)]
    for level, collection_id in enumerate(ids):
        parent_id = ids[level - 1] if level else None
        store.collections.add(Collection(id=collection_id, name=f"L{level}", parent_id=parent_id))

    response = client.get("/collections")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    expected = "[" + "".join(
        f'{{"id":"{collection_id}","name":"L{level}",'
        f'"parent_id":{"null" if level == 0 else f"{chr(34)}{ids[level - 1]}{chr(34)}"},'
        '"children":['
        for level, collection_id in enumerate(ids)
    ) + "]}" * depth + "]"
    assert response.text == expected

    response = client.patch(f"/collections/{ids[0]}", json={"parent_id": ids[-1]})
    assert response.status_code == 400
    assert client.delete(f"/collections/{ids[-1]}").status_code == 204


def test_list_response_schema_is_documented_in_openapi(client):
    spec = client.get("/openapi.json").json()
    schema = spec["paths"]["/collections"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert schema["type"] == "array"
    assert schema["items"] == {"$ref": "#/components/schemas/CollectionTreeNode"}
    node_schema = spec["components"]["schemas"]["CollectionTreeNode"]
    assert set(node_schema["required"]) == {"id", "name", "parent_id", "children"}
    assert node_schema["properties"]["children"]["items"] == {
        "$ref": "#/components/schemas/CollectionTreeNode"
    }

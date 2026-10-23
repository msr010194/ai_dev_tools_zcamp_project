from typing import Annotated

from fastapi import Depends

from app.dependencies import get_store
from app.repositories.memory import InMemoryStore

# Stores seen by the fresh-store tests; holding references keeps `is not` meaningful.
_seen_stores: list[InMemoryStore] = []


def test_client_request_receives_the_store_fixture(app, client, store):
    @app.get("/_probe/store")
    def probe(request_store: Annotated[InMemoryStore, Depends(get_store)]) -> dict[str, bool]:
        return {"same": request_store is store}

    assert client.get("/_probe/store").json() == {"same": True}


def test_fresh_store_per_test_first(app, store):
    assert store is app.state.store
    assert all(store is not seen for seen in _seen_stores)
    _seen_stores.append(store)


def test_fresh_store_per_test_second(app, store):
    assert store is app.state.store
    assert all(store is not seen for seen in _seen_stores)
    _seen_stores.append(store)

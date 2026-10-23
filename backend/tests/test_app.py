import ast
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import main as app_main
from app.dependencies import get_settings, get_store
from app.main import app as module_app
from app.main import create_app
from app.repositories.memory import InMemoryStore
from app.routers import health
from app.settings import Settings


def add_probe_routes(app: FastAPI) -> None:
    """Attach test-only routes that report which settings/store the dependencies resolve to."""

    @app.get("/_probe/store")
    def probe_store(store: Annotated[InMemoryStore, Depends(get_store)]) -> dict[str, int]:
        return {"store_id": id(store)}

    @app.get("/_probe/settings")
    def probe_settings(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
        return {"app_name": settings.app_name}


# Settings


def test_settings_default_app_name(monkeypatch):
    monkeypatch.delenv("NOTES_APP_NAME", raising=False)
    assert Settings().app_name == "Notes API"


def test_settings_reads_app_name_from_environment(monkeypatch):
    monkeypatch.setenv("NOTES_APP_NAME", "From Env")
    assert Settings().app_name == "From Env"


def test_create_app_uses_given_settings_for_title():
    assert create_app(Settings(app_name="Test API")).title == "Test API"


def test_default_app_title_is_notes_api(monkeypatch):
    monkeypatch.delenv("NOTES_APP_NAME", raising=False)
    assert create_app().title == "Notes API"
    assert module_app.title == "Notes API"


def test_get_settings_returns_settings_app_was_created_with():
    settings = Settings(app_name="Injected")
    app = create_app(settings)
    add_probe_routes(app)
    with TestClient(app) as client:
        assert client.get("/_probe/settings").json() == {"app_name": "Injected"}
    assert app.state.settings is settings


# Store and dependency injection


def test_create_app_puts_a_store_on_app_state():
    app = create_app()
    assert isinstance(app.state.store, InMemoryStore)


def test_each_app_gets_its_own_store():
    assert create_app().state.store is not create_app().state.store


def test_store_is_shared_across_requests_within_one_app():
    app = create_app()
    add_probe_routes(app)
    with TestClient(app) as client:
        first = client.get("/_probe/store").json()["store_id"]
        second = client.get("/_probe/store").json()["store_id"]
    assert first == second == id(app.state.store)


def test_get_store_returns_store_of_app_handling_request():
    app_a, app_b = create_app(), create_app()
    add_probe_routes(app_a)
    add_probe_routes(app_b)
    with TestClient(app_a) as client_a, TestClient(app_b) as client_b:
        assert client_a.get("/_probe/store").json()["store_id"] == id(app_a.state.store)
        assert client_b.get("/_probe/store").json()["store_id"] == id(app_b.state.store)


def test_health_route_is_defined_in_router_and_included_by_app():
    assert [route.path for route in health.router.routes] == ["/health"]
    main_source = ast.parse(Path(app_main.__file__).read_text(encoding="utf-8"))
    decorated = [
        node.name
        for node in ast.walk(main_source)
        if isinstance(node, ast.FunctionDef) and node.decorator_list
    ]
    assert decorated == []
    with TestClient(module_app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_routers_and_services_do_not_import_memory_repositories():
    app_dir = Path(app_main.__file__).parent
    offenders = [
        path.relative_to(app_dir).as_posix()
        for package in ("routers", "services")
        for path in (app_dir / package).glob("*.py")
        if "repositories.memory" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []

"""Liveness check."""

from fastapi import APIRouter

from app.schemas.health import Health

router = APIRouter(tags=["health"])


@router.get(
    "/health", response_model=Health, operation_id="getHealth", summary="Check that the API is up"
)
def health() -> Health:
    return Health(status="ok")

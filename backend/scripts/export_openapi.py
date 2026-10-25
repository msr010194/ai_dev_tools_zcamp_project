"""Write the app's OpenAPI document to `contract/openapi.json` at the repo root.

Run from `backend/`:  uv run python -m scripts.export_openapi
"""

import json
import sys
from pathlib import Path
from typing import Any

from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "contract" / "openapi.json"
EXPORT_COMMAND = "cd backend; uv run python -m scripts.export_openapi"


def render_spec(spec: dict[str, Any]) -> str:
    """Deterministic text: 2-space indent, keys in the app's order, trailing newline."""
    return json.dumps(spec, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    text = render_spec(create_app().openapi())
    try:
        SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SPEC_PATH.open("w", encoding="utf-8", newline="\n") as file:
            file.write(text)
    except OSError as error:
        print(f"Could not write {SPEC_PATH}: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {SPEC_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

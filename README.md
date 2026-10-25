# ai_dev_tools_zcamp_project
Final project for DataTalksClub course - https://datatalks.club/courses/ai-dev-tools-zoomcamp/

## Running the tests

Backend (Python 3.12+, [uv](https://docs.astral.sh/uv/)):

```
cd backend
uv sync
uv run pytest
```

Frontend (Node 20+):

```
cd frontend
npm install
npm test
```

## API contract

The OpenAPI spec in [`contract/openapi.json`](contract/openapi.json) is generated from the
backend and committed. After changing any endpoint or schema, regenerate it:

```
cd backend
uv run python -m scripts.export_openapi
```

`uv run pytest` fails if the committed spec is out of date.

The frontend's API types (`frontend/src/api/schema.ts`) are generated from that spec, so after
re-exporting it, regenerate them too:

```
cd frontend
npm run generate:api   # rewrite src/api/schema.ts from contract/openapi.json
npm run check:api      # exit 1 if src/api/schema.ts is out of date (changes nothing)
```

`src/api/client.ts` wraps the generated types in a typed fetch client (`createApiClient(baseUrl)`).

# Task Backlog

Assumed stack (see plan.md): React (Vite, TypeScript) frontend, Python (FastAPI) REST API, PostgreSQL. Single-user demo: no accounts, login, search, tag merging, prompt templates, or graph view.

Sequencing: the frontend is built first against a mock data layer, and the backend is built next with in-memory storage. The OpenAPI contract then fixes the interface between the two, and PostgreSQL replaces the in-memory storage afterwards.

## Project Setup

1. Set up empty project with a passing test
Goal: Have a monorepo skeleton where one test runs and passes for both backend and frontend.
Description: Create `backend/` (Python 3.12+, FastAPI, dependencies managed with uv or Poetry, pytest with FastAPI's `TestClient`) and `frontend/` (Vite + React + TypeScript, Vitest + React Testing Library). Each package gets one trivial passing test (e.g. a `/health` endpoint on the backend, an `App` render on the frontend) and a single command to run it (`pytest` and `npm test`). Add a root README section on how to run the tests.

## A. Build a frontend

All frontend tasks work against a mock API layer (e.g. MSW or in-memory fixtures) until the contract and generated client exist in section C.

2. Frontend app shell, routing and mock data layer
Goal: Have a navigable React app that reads and writes data through a swappable data layer.
Description: Set up React Router with placeholder pages (Home, Timeline, Tags, Collections) and a basic layout. Define a small data-access interface (collections, tags, notes) with an in-memory mock implementation, so later tasks can swap in a real API client. Add a test that the routes render.

3. Type-specific field components
Goal: Render the right extra fields for each note Type.
Description: Build standalone field components for Journal (mood, free-text prompt that becomes read-only once set, retrospective toggle with weekly/monthly period), Reference (sub-kind dropdown, link), Plan (target date, state dropdown, checklist editor with text and done checkbox), and Memory (when, where). Idea has none. Test that each Type shows only its own fields.

4. Shared note editor with Collection and Tag pickers
Goal: Create and edit the common parts of any note.
Description: Build an editor shell with a body field, a nested Collection picker (required), and a multi-select Tag picker restricted to existing tags (optional). It takes a Type, renders that Type's field components in a slot, and saves through the data layer.

5. Home page with three intent entry points
Goal: Present Capture, Reflect, and Preserve as the front door.
Description: Build a home view with three prominent actions that open the note editor pre-set to Idea, Journal, and Memory respectively, with a quick switch to Reference or Plan for Capture. Test that each entry sets the correct default Type.

6. Timeline view
Goal: Show the unified chronological timeline as the default landing view.
Description: Render notes newest-first with "load more", showing Type, Collection, tags, and a body preview. Add filters for Collection, Tag, and an Untagged toggle; selecting a tag anywhere in the app opens the timeline filtered by it. Test rendering and filter behaviour using the mock data layer.

7. Collections management UI
Goal: Let users add, rename, move, and delete Collections.
Description: Build a tree view with inline add, rename, and delete actions, and a way to move a collection under a new parent. Show a clear message when deleting a non-empty collection is rejected.

8. Tags management UI
Goal: Let users curate a fixed tag list.
Description: Build a tags page listing tags with note counts, with actions to create and rename a tag. Each tag links to the timeline filtered by that tag.

9. Resurfacing panel
Goal: Surface forgotten notes on the home page.
Description: Add a panel that shows a few older notes, with Memories favoured, and records each as seen. Include a "show another" action and test that the seen call is made on the data layer.

## B. Build a backend

All backend tasks store data in memory behind repository interfaces, so no database is needed until section D.

10. Backend structure with in-memory repositories
Goal: Establish the layering that every later backend task builds on.
Description: Organise the FastAPI app into routers, services, and repository interfaces with in-memory implementations and dependency injection, plus a settings module (e.g. pydantic-settings). Provide a test fixture that gives each test a fresh in-memory store.

11. Collections API
Goal: Add, rename, move and delete hierarchical Collections.
Description: Implement `GET /collections` (tree), `POST`, `PATCH /{id}` (rename/move), and `DELETE /{id}` with Pydantic schemas and proper error codes. Prevent a collection from becoming its own descendant. Document and test delete behaviour for collections that still contain notes or children (e.g. reject with 409), and nesting at least three levels deep.

12. Tags API
Goal: Manage a curated tag list.
Description: Implement list, create, and rename endpoints for tags with unique, case-insensitive names. Tags are created only through this API, never implicitly from notes. Test duplicate-name rejection.

13. Notes API with shared fields
Goal: Create, read, update, and delete notes of any Type using only the common fields.
Description: Implement `POST /notes`, `GET /notes/{id}`, `PATCH /notes/{id}`, `DELETE /notes/{id}` with `type` (journal, idea, reference, plan, memory), `body`, a required single `collection_id`, and a `tag_ids` list that may be empty. Use Pydantic discriminated unions on `type` so type-specific fields can be added per Type. Test the single-collection rule and zero-tag notes.

14. Journal note fields
Goal: Support Journal-specific data.
Description: Add `entry_date` (auto-filled to now if omitted), `mood` (free text), `prompt` (optional free text, read-only once set), and an `is_retrospective` flag with optional period (weekly/monthly). Reject fields that do not belong to the Type. Test that updating `prompt` after creation is rejected.

15. Reference note fields
Goal: Support Reference-specific data.
Description: Add `sub_kind` (written, visual, audio) and `link` (optional, loosely validated URL). Validate on create and update, and test invalid sub-kinds and malformed links.

16. Plan note fields and checklist
Goal: Support Plan-specific data including checklist items.
Description: Add `target_date`, `state` (not_started, in_progress, done, abandoned), and a checklist of items (`text`, `done`, `position`). Support adding, toggling, reordering, and removing items. Test state values and that items go away with the plan.

17. Memory note fields
Goal: Support Memory-specific data.
Description: Add optional free-text `when` and `where` fields to Memory notes. Also track `last_resurfaced_at` and `resurface_count` on every note, which the resurfacing endpoint will use. Test create and update.

18. Timeline endpoint with filtering and pagination
Goal: Serve the unified chronological timeline.
Description: Implement `GET /timeline` returning notes of all Types newest-first with cursor-based pagination. Support optional filters for `collection_id` (optionally including descendants), `type`, `tag_id`, and `untagged=true`. Test ordering, pagination stability, descendant inclusion, and that a note drops out of the untagged view once a tag is attached.

19. Resurfacing endpoint
Goal: Return older notes for spaced, semi-random resurfacing.
Description: Implement `GET /resurface` selecting a small set of notes weighted toward Memories, excluding recently created or recently resurfaced notes, using `last_resurfaced_at` and `resurface_count`. Add `POST /notes/{id}/resurfaced` to record that a note was shown. Make the random source injectable so tests are deterministic.

## C. Define frontend/backend communication with an OpenAPI contract

20. Export and commit the OpenAPI spec
Goal: Make the FastAPI-generated spec the committed source of truth for the API.
Description: Add a script that writes the app's OpenAPI document to a file in the repo (e.g. `openapi.json`), and ensure every endpoint has tags, summaries, and explicit request and response models. Add a test that fails if the committed file is out of date with the app.

21. Uniform error format in the contract
Goal: Give every error response one documented shape.
Description: Add central exception handlers returning a consistent JSON error body, including for Pydantic validation errors, and declare the error response models in the OpenAPI spec. Test a representative 400, 404, 409, and 422.

22. Generate a typed TypeScript client from the spec
Goal: Produce the frontend's API types and client from the contract.
Description: Add a generator (e.g. openapi-typescript or Orval) driven by the committed spec, an npm script to regenerate it, and a check that the generated output is up to date. No existing screens need to change in this task.

23. Switch the frontend from mocks to the generated client
Goal: Run the frontend against the real backend.
Description: Implement the frontend data-access interface using the generated client, configured with a base URL and a dev proxy or CORS settings. Keep the mock implementation available for component tests, and verify the main flows by hand against the running backend.

## D. Add database or persistent storage

24. Add Postgres via Docker Compose and a DB connection
Goal: Run a local Postgres and connect to it from the backend.
Description: Add a `docker-compose.yml` that starts Postgres with a named volume, read the connection string from environment variables (with a `.env.example`), and set up a SQLAlchemy engine and session. Add a test or script that verifies a `SELECT 1` succeeds.

25. Set up database migrations tooling
Goal: Be able to create, apply and roll back schema migrations from the command line.
Description: Configure Alembic with SQLAlchemy models as the schema source and document the upgrade and downgrade commands. Create an initial empty migration to prove the workflow against the Docker Postgres.

26. Persist Collections
Goal: Store Collections in Postgres instead of memory.
Description: Add a `collections` table with a self-referencing `parent_id` and a SQLAlchemy implementation of the Collections repository interface, selectable via settings. Keep the existing API tests passing against both implementations, and test the tree queries for nesting at least three levels deep.

27. Persist Tags and note-tag links
Goal: Store Tags and their links to notes in Postgres.
Description: Add `tags` (unique name, case-insensitive) and a `note_tags` join table, and implement the Tags repository. Run the existing tags API tests against it.

28. Persist Notes and Type-specific data
Goal: Store all five note Types in Postgres.
Description: Add a `notes` table with the common fields and a required `collection_id`, type-specific columns or tables for Journal, Reference, Plan, and Memory, and a `plan_checklist_items` table. Implement the Notes repository, including the resurfacing columns, and run the notes API tests against it.

29. SQL implementations of timeline and resurfacing queries
Goal: Make the timeline, untagged filter, and resurfacing queries work efficiently in Postgres.
Description: Implement these queries in SQL (including recursive descendant lookup for Collections and weighted selection for resurfacing) and add indexes on creation date, `collection_id`, and `note_tags`. Verify results match the existing endpoint tests.

30. Seed script with sample data
Goal: Populate a dev database with realistic data.
Description: Write a script that creates nested collections, tags, and a mix of notes of all five Types across several months, including retrospectives and Memories for resurfacing. Make it resettable so it can be rerun for demos.

## E. Test the application

31. Backend tests against a real Postgres
Goal: Run the backend suite reliably against the database.
Description: Add pytest fixtures that create a test database, apply migrations, and isolate each test (transaction rollback or truncation). Document how to run the suite locally and with the Docker Postgres.

32. API contract tests
Goal: Check that the running API conforms to its OpenAPI spec.
Description: Add automated tests (e.g. Schemathesis) that exercise the endpoints in the committed spec and verify status codes and response shapes. Wire them into the backend test command.

33. End-to-end smoke test
Goal: Verify the core journey works across frontend, backend, and database.
Description: Add a Playwright test that creates a collection and a tag, creates a note, and sees it in the timeline. Run it against the full local stack and document how to execute it.

34. CI pipeline
Goal: Run all checks automatically on every push.
Description: Add a GitHub Actions workflow that installs dependencies, starts a Postgres service, runs Alembic migrations, and runs backend (pytest, ruff, mypy or pyright) and frontend (Vitest, ESLint, `tsc`) checks, plus the contract tests. Fail the build on any error.

## F. Containerize the application

35. Backend Dockerfile
Goal: Package the API as a container image.
Description: Add a multi-stage Dockerfile for the FastAPI app served with uvicorn, running as a non-root user, with configuration from environment variables and a health check. Add a `.dockerignore` and document how to build and run it.

36. Frontend Dockerfile
Goal: Package the built React app as a container image.
Description: Add a multi-stage Dockerfile that builds the Vite app and serves the static files with nginx, with the API base URL configurable at build or run time. Add a `.dockerignore` and document how to build and run it.

37. Full stack Docker Compose
Goal: Run the whole application with one command.
Description: Extend Docker Compose to run Postgres, the API (applying Alembic migrations on start), and the frontend, with environment variables documented in `.env.example`. Document the command in the README, including how to seed sample data.

## G. Deploy it so others can try it

38. Choose a hosting platform and provision Postgres
Goal: Have a hosted database ready for the deployed API.
Description: Pick a platform (e.g. Render, Fly.io, Railway, or a cloud container service), record the choice and reasoning in the README, and provision a managed Postgres instance. Store its connection string as a secret rather than in the repo.

39. Deploy the backend
Goal: Get the API running at a public URL.
Description: Deploy the backend image, configure secrets and environment variables, run migrations against the hosted database, and set CORS to allow the frontend origin. Verify the health endpoint and the `/docs` page.

40. Deploy the frontend
Goal: Get the React app running at a public URL.
Description: Deploy the frontend (container or static host), point it at the deployed API, and confirm the main flows work, including creating a note.

41. Continuous deployment and a public README
Goal: Make deployments repeatable and tell others how to try the app.
Description: Add a workflow that deploys on merge to the main branch after CI passes, and runs a post-deploy smoke check. Add the live URL, sample data instructions, a short architecture overview, and a note that the demo is open with no login (anyone can edit its data, so the seed script can reset it) to the README.

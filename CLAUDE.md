# GTD Task Manager (todo-api)

## Stack
- FastAPI + SQLAlchemy + SQLite, Python 3.14, uv
- Deployed on Fly.io (region: ord, app: gtd-api)

## Commands
- `uv run pytest` or `python -m pytest` — run tests (235 tests)
- `uvicorn app.main:app --reload` — local dev server (port 8000)

## Testing
- TDD: write failing test first, then implement
- Use `httpx.MockTransport` for HTTP service mocking (not `unittest.mock.patch` on internals)
- `tests/test_docs.py` validates all routes are documented in README — update README when adding endpoints

## Architecture
- Donor DB integration: `app/services/donor_client.py` fetches tasks from the Donor Management DB via HTTP
- DonorClient is a module-level singleton with in-memory cache (5min TTL)
- Anti-corruption layer: `_map_task()` translates donor domain → GTD domain
- Status mapping: pending→next_action, completed→completed, cancelled→deleted
- Real donor data uses status "0" (from DonorHub import), mapped to next_action by default

## Deployment
- Deploy donor DB (sr-assistant) BEFORE this app — GTD depends on it at runtime
- Fly.io .internal DNS does NOT resolve across regions — use public URL (https://donor-management.fly.dev)
- `DONOR_DB_URL` and `DONOR_DB_API_KEY` set via `fly secrets set`
- Dashboard at /dashboard does not yet show donor tasks

## Git
- Merge with `--no-ff`

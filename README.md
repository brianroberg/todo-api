# GTD API

A RESTful API implementing David Allen's **Getting Things Done (GTD)** methodology, built with FastAPI and SQLite.

## GTD Concepts

This API implements the core GTD workflow:

- **Inbox** - Capture bucket for unprocessed items
- **Next Actions** - Concrete, actionable tasks you can do right now
- **Someday/Maybe** - Items you might do but aren't committed to yet
- **Projects** - Multi-step outcomes requiring more than one action
- **Tickler** - Time-delayed items that surface on a future date
- **Areas of Responsibility** - Ongoing roles and accountabilities
- **Tags** - Flexible categorization (including @context-style labels like `@home`, `@phone`, `@waiting_for`)

## Quick Start

### Prerequisites

- Python 3.11+
- pip or uv

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd todo-api

# Install dependencies
pip install -e .

# Or with uv
uv pip install -e .
```

### Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

### Running Locally

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

This API uses API key authentication. All requests (except creating an API key) require the `X-API-Key` header.

### Creating an API Key

```bash
# Create a new API key
curl -X POST http://localhost:8000/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Key"}'
```

Response:
```json
{
  "id": 1,
  "name": "My API Key",
  "api_key": "gtd_abc123...",
  "message": "Save this API key - it will not be shown again"
}
```

**Important:** Save the `api_key` value - it's only shown once!

### Using the API Key

Include the key in all subsequent requests:

```bash
curl http://localhost:8000/inbox \
  -H "X-API-Key: gtd_abc123..."
```

### Securing API Key Creation (Production)

Set `ADMIN_KEY` in your environment to require authorization for creating new API keys:

```bash
# In .env or environment
ADMIN_KEY=your-secret-admin-key
```

Then include it when creating keys:
```bash
curl -X POST http://localhost:8000/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "My Key", "admin_key": "your-secret-admin-key"}'
```

## API Overview

### Authentication

```
POST /auth/keys           - Create a new API key
GET  /auth/keys/current   - Get info about current API key
DELETE /auth/keys/current - Revoke current API key
```

### GTD Endpoints

```
/inbox            - Capture and process items
/next-actions     - Actionable tasks
/someday-maybe    - Uncommitted items
/projects         - Multi-step outcomes
/tickler          - Time-delayed reminders
/areas            - Areas of responsibility
/tags             - Flexible categorization
/review           - Weekly review helpers
```

### Example: GTD Workflow

```bash
# 1. Create an API key
API_KEY=$(curl -s -X POST http://localhost:8000/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "demo"}' | jq -r '.api_key')

# 2. Capture to inbox
curl -X POST http://localhost:8000/inbox \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Call dentist about appointment"}'

# 3. Process inbox item to next action
curl -X POST http://localhost:8000/inbox/1/process \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"destination": "next_action"}'

# 4. Create a project
curl -X POST http://localhost:8000/projects \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Plan vacation", "outcome": "Flights and hotel booked, itinerary ready"}'

# 5. Add action to project
curl -X POST http://localhost:8000/projects/1/actions \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Research flight prices"}'

# 6. Create a tag for contexts
curl -X POST http://localhost:8000/tags \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "@phone", "color": "#3498db"}'

# 7. Weekly review - check for stale projects
curl http://localhost:8000/review/stale-projects \
  -H "X-API-Key: $API_KEY"
```

## Deployment to Fly.io

### Prerequisites

- [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/)
- Fly.io account

### Deploy

```bash
# Login to Fly
fly auth login

# Create the app (first time only)
fly launch --no-deploy

# Create a volume for the SQLite database
fly volumes create gtd_data --size 1 --region ord

# Set the admin key for API key creation (optional but recommended)
fly secrets set ADMIN_KEY=$(openssl rand -hex 32)

# Deploy
fly deploy
```

### Post-deployment

Your API will be available at `https://gtd-api.fly.dev` (or your custom app name).

Create your first API key:
```bash
curl -X POST https://gtd-api.fly.dev/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "production", "admin_key": "your-admin-key"}'
```

## Project Structure

```
todo-api/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application entry point
│   ├── config.py         # Settings from environment
│   ├── database.py       # SQLite/SQLAlchemy setup
│   ├── auth/
│   │   ├── router.py     # API key endpoints
│   │   ├── service.py    # API key management
│   │   └── dependencies.py
│   ├── models/
│   │   └── models.py     # SQLAlchemy models
│   ├── schemas/
│   │   └── schemas.py    # Pydantic request/response models
│   └── routers/
│       ├── inbox.py
│       ├── next_actions.py
│       ├── someday_maybe.py
│       ├── projects.py
│       ├── tickler.py
│       ├── areas.py
│       ├── tags.py
│       └── review.py
├── pyproject.toml
├── Dockerfile
├── fly.toml
└── README.md
```

## License

MIT

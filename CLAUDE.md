# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database and create default users
python init_data.py

# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Default accounts: `admin/admin123`, `user/user123`

## Architecture Overview

**Backend**: FastAPI + SQLAlchemy + SQLite  
**Frontend**: Jinja2 templates + Vue.js 3 + Bootstrap  
**API docs**: http://localhost:8000/docs

### Project Structure

```
ai_manage_platform/
├── app/
│   ├── api/              # API routes (one module per feature)
│   ├── core/             # Core utilities (config, database, security, exceptions, audit)
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   └── main.py           # App entry point
├── templates/            # Jinja2 HTML templates
├── static/               # Static assets
├── data/                 # SQLite database
└── tests/                # Integration tests
```

### API Module Pattern

Each feature module follows this pattern:
- `app/api/<feature>.py` - Routes with CRUD operations
- Models in `app/models/models.py`
- Schemas in `app/schemas/schemas.py`
- Templates in `templates/<feature>.html`

Routes are registered in `app/api/__init__.py` with prefix `/api/<feature>`

### Key Conventions

**Pagination**: All list endpoints use `skip`/`limit` params, return `PaginatedResponse[T]`

**Permissions**: Check via `can_edit_resource()` / `can_delete_resource()` in `app/api/auth.py`

**Workflows**: Resources (applications, datasets, models, agents, compute) can bind to workflow definitions for multi-step approval

**Exceptions**: Custom exceptions in `app/core/exceptions.py` with global handlers registered in `main.py`

**Audit Logging**: Use `log_action()`, `log_create()`, `log_update()`, `log_delete()` from `app/core/audit.py`

### Adding a New Module

1. Add model to `app/models/models.py`
2. Add schema to `app/schemas/schemas.py`
3. Create route in `app/api/<module>.py`
4. Register route in `app/api/__init__.py`
5. Add page template in `templates/`
6. Add page route in `app/main.py`

### Testing

Tests are integration tests requiring a running server:

```bash
# Start server first
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run tests
python tests/test_workflow.py
```

### Database Migrations

Migration scripts are in `scripts/migrations/`. Run manually as needed.

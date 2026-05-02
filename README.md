# Task Management API

## Overview

This backend implements a task/project management system using FastAPI, SQLite, JWT authentication, and role-based authorization.

Supported features:
- User registration and login with JWT tokens
- Admin, manager, and employee roles
- CRUD operations for projects and tasks
- Task status lifecycle validation (todo → in_progress → done)
- Protected routes and permissions enforcement
- Request validation using Pydantic schemas

## Installation

```bash
cd your-folder-name
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the App

### 1. Start Redis Server (Required)

The application uses Redis for caching. You **must** start Redis before running the app.

#### On Linux (Ubuntu/Debian):
```bash
sudo systemctl start redis-server
redis-cli ping
# Output: PONG
```

#### On macOS (with Homebrew):
```bash
brew services start redis
redis-cli ping
# Output: PONG
```

#### On Windows:
Download and install from: https://github.com/microsoftarchive/redis/releases

### 2. Start FastAPI Application

```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

### 3. Monitor Cache (Optional)

In another terminal, view real-time cache operations:
```bash
redis-cli MONITOR
```

---

## Caching System

This project uses **Redis** for distributed in-memory caching with automatic TTL expiration:

- **User cache**: 5 minutes — caches authenticated users to reduce database queries
- **Project cache**: 10 minutes — caches project lookups and the projects list
- **Task cache**: 5 minutes — reserved for future task caching

### Cache Configuration

Edit `.env` to customize Redis settings:
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=None

CACHE_USER_TTL=300
CACHE_PROJECT_TTL=600
CACHE_TASK_TTL=300
```

### What Gets Cached

✓ User lookups by ID (authentication)  
✓ Project by ID (single project fetch)  
✓ All projects list (GET /api/v1/projects)  
✓ Project existence checks (during task creation)

Cache is automatically invalidated when:
- New project is created
- Project is updated
- Task is created/updated (affects project)

See [REDIS_SETUP.md](REDIS_SETUP.md) for detailed Redis documentation.  
See [CACHING_GUIDE.md](CACHING_GUIDE.md) for caching architecture details.

---

## Default Admin Account

A default admin user is created automatically if none exists:
- username: `admin`
- password: `admin123`

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` — register a new employee user
- `POST /api/v1/auth/login` — obtain JWT access token

### Users
- `GET /api/v1/users/me` — current authenticated user
- `GET /api/v1/users` — list users (admin only)
- `GET /api/v1/users/{user_id}` — read user by ID

### Projects
- `POST /api/v1/projects` — create a project (admin or manager)
- `GET /api/v1/projects` — list projects
- `GET /api/v1/projects/{project_id}` — read a project
- `PUT /api/v1/projects/{project_id}` — update a project (admin or manager)
- `DELETE /api/v1/projects/{project_id}` — delete a project (admin only)

### Tasks
- `POST /api/v1/tasks` — create a task (admin or manager)
- `GET /api/v1/tasks` — list tasks with optional filters
- `GET /api/v1/tasks/{task_id}` — read a task
- `PUT /api/v1/tasks/{task_id}` — update a task (assignee or manager/admin)
- `DELETE /api/v1/tasks/{task_id}` — delete a task (admin only)

## Notes

- Tasks can be filtered by status, priority, assignee ID, or project ID.
- Employees may only update tasks assigned to them.
- Status transitions are enforced: `todo` → `in_progress` → `done`.

---

## Authorization & Business Logic Layer (v2)

### New files added

| File | Purpose |
|------|---------|
| `app/core/authorization.py` | Role-based dependency helpers (`require_admin`, `require_admin_or_pm`, `require_roles`) |
| `app/services/project_service.py` | Project CRUD business logic with ownership checks |
| `app/services/task_service.py` | Task CRUD + status FSM validation + role-aware filtering |
| `app/api/v2/projects_api_v2.py` | Role-gated project endpoints (`/v2/projects/...`) |
| `app/api/v2/tasks_api_v2.py` | Role-gated task endpoints with filtering (`/v2/tasks/...`) |
| `app/api/v2/router_v2.py` | Assembles both v2 sub-routers under `/v2` |

### Wiring the v2 router (one-time step)

Add **two lines** to `app/api/router_api.py`:

```python
from app.api.v2.router_v2 import v2_router          # ← add
api_router.include_router(v2_router)                 # ← add
```

This exposes all v2 endpoints under `/api/v1/v2/...`.  
If you prefer `/api/v2/...`, include `v2_router` directly in `main.py` with `prefix="/api/v2"`.

### Role matrix

| Action | admin | project_manager | employee |
|--------|-------|-----------------|----------|
| Create project | ✓ | ✓ | ✗ |
| Read projects | ✓ | ✓ | ✓ |
| Update project | ✓ | ✓ (own only) | ✗ |
| Delete project | ✓ | ✗ | ✗ |
| Create task | ✓ | ✓ | ✗ |
| Read tasks | ✓ (all) | ✓ (all) | ✓ (own only) |
| Update task — any field | ✓ | ✓ | ✗ |
| Update task — status only | ✓ | ✓ | ✓ (own task) |
| Delete task | ✓ | ✗ | ✗ |

### Task status lifecycle (enforced for all roles)

```
todo  ──►  in_progress  ──►  done
             ◄──────────────  (rollback: done → in_progress)
todo  ◄──  in_progress          (rollback: in_progress → todo)
```

Invalid transitions return **HTTP 422**.  
New tasks must always start as `todo`.

### Filtering (GET /v2/tasks/)

| Query param | Values | Scope |
|-------------|--------|-------|
| `?status=` | `todo` \| `in_progress` \| `done` | all roles |
| `?priority=` | `low` \| `medium` \| `high` | all roles |
| `?assignee_id=` | any user ID | admin / project_manager only |

Employees are automatically scoped to their own tasks — `assignee_id` is ignored for them.

### v2 API Endpoints

```
POST   /api/v1/v2/projects/          Create project  (admin, pm)
GET    /api/v1/v2/projects/          List projects   (all)
GET    /api/v1/v2/projects/{id}      Get project     (all)
PUT    /api/v1/v2/projects/{id}      Update project  (admin, pm-owner)
DELETE /api/v1/v2/projects/{id}      Delete project  (admin)

POST   /api/v1/v2/tasks/             Create task     (admin, pm)
GET    /api/v1/v2/tasks/             List tasks      (role-scoped, filterable)
GET    /api/v1/v2/tasks/{id}         Get task        (role-scoped)
PATCH  /api/v1/v2/tasks/{id}         Update task     (field-restricted by role)
DELETE /api/v1/v2/tasks/{id}         Delete task     (admin)
```

---

## View database

Install SQLite CLI if needed:

```bash
sudo apt install sqlite3
```

Open the database:

```bash
sqlite3 task_managment.db
```

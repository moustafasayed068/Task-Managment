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

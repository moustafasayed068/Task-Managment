# 📋 Task Management API

A production-ready RESTful API for managing projects and tasks, built with **FastAPI**, **SQLAlchemy**, **Redis**, and **JWT authentication**. Features role-based access control, a task-status state machine, Redis caching, structured logging via Loguru, and real-time email security alerts.

---

## 🚀 Features

| Category             | Details                                                                          |
| -------------------- | -------------------------------------------------------------------------------- |
| **Authentication**   | JWT-based login & registration with bcrypt password hashing                      |
| **Authorization**    | Three roles: `admin`, `project_manager`, `employee` — enforced at every endpoint |
| **Projects & Tasks** | Full CRUD with ownership checks and assignee scoping                             |
| **Task Workflow**    | Status lifecycle FSM: `todo → in_progress → done` with rollback support          |
| **Caching**          | Redis-backed Cache-Aside pattern with automatic TTL and invalidation             |
| **Logging**          | Loguru with professional terminal output + rotating file sinks (multi-stream)    |
| **Security Alerts**  | SMTP email notifications on failed logins and unauthorized access                |
| **Testing**          | Pytest suite covering auth, projects, and tasks                                  |

---

## 📁 Project Structure

```
Task-Managment/
├── app/
│   ├── main.py                     # FastAPI app factory & lifespan
│   ├── api/
│   │   ├── router_api.py           # Root router (mounts all sub-routers)
│   │   ├── auth_api.py             # POST /register, /login, /me
│   │   ├── users_api.py            # User management (admin delete)
│   │   ├── projects_api.py         # v1 project CRUD
│   │   ├── tasks_api.py            # v1 task CRUD
│   │   └── v2/
│   │       ├── router_v2.py        # v2 sub-router assembly
│   │       ├── projects_api_v2.py  # Role-gated project endpoints
│   │       └── tasks_api_v2.py     # Role-gated task endpoints + filtering
│   ├── core/
│   │   ├── config_core.py          # Pydantic Settings (.env loader)
│   │   ├── security.py             # JWT encode/decode, bcrypt helpers
│   │   ├── dependencies.py         # OAuth2 token extraction, require_role
│   │   ├── authorization.py        # require_admin, require_admin_or_pm, require_roles
│   │   ├── logger_core.py          # Loguru configuration (console + file sinks)
│   │   ├── middleware.py            # ASGI request/response logging middleware
│   │   └── cache_core.py           # Redis cache decorators & invalidation
│   ├── db/
│   │   ├── base_db.py              # SQLAlchemy declarative base
│   │   └── session_db.py           # Engine & session factory
│   ├── models/
│   │   ├── user_models.py          # UserModel (id, username, email, role, password_hash)
│   │   ├── project_models.py       # ProjectModel (id, name, description, owner_id)
│   │   └── task_models.py          # TaskModel (id, title, status, priority, assignee_id, project_id)
│   ├── schemas/
│   │   ├── auth_schemas.py         # UserRegister, Token, LoginRequest
│   │   ├── project_schemas.py      # ProjectCreate, ProjectResponse
│   │   ├── task_schemas.py         # TaskCreate, TaskUpdate, TaskResponse
│   │   └── user_schemas.py         # UserResponse
│   └── services/
│       ├── email_service.py        # SMTP email alerts (login failures, unauthorized access)
│       ├── project_service.py      # Project business logic + ownership enforcement
│       └── task_service.py         # Task business logic + status FSM + role-aware filtering
├── tests/
│   ├── conftest.py                 # Test fixtures (in-memory SQLite, test client)
│   ├── test_auth.py                # Auth endpoint tests
│   ├── test_projects.py            # Project CRUD tests
│   └── test_tasks.py               # Task CRUD + workflow tests
├── logs/                           # Auto-created: app.log, errors.log
├── .env                            # Environment variables (SMTP, Redis, JWT, DB)
├── requirements.txt                # Python dependencies
└── README.md
```

---

## ⚙️ Installation

### Prerequisites

- Python 3.11+
- Redis server (for caching)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd Task-Managment

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
# ── App ──────────────────────────────────────────────────────
APP_NAME="Task Management API"
API_PREFIX="/api/v1"

# ── Security ─────────────────────────────────────────────────
SECRET_KEY=your-super-secret-key-change-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── Database ─────────────────────────────────────────────────
DATABASE_URL=sqlite:///./task_management.db

# ── Redis ────────────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_redis_password

# ── Cache TTLs (seconds) ────────────────────────────────────
CACHE_USER_TTL=300
CACHE_PROJECT_TTL=600
CACHE_TASK_TTL=300

# ── SMTP / Email Alerts ─────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
ALERT_EMAIL_FROM=your-email@gmail.com
ALERT_EMAIL_TO=recipient@example.com
```

> **Gmail users**: Use an [App Password](https://support.google.com/accounts/answer/185833), not your real password. Enable 2-Step Verification first, then generate an App Password under _Google Account → Security → App Passwords_.

---

## 🏃 Running the App

### 1. Start Redis (required for caching)

**Windows** — Download from [Microsoft Archive](https://github.com/microsoftarchive/redis/releases), or use Docker:

```bash
docker run -d -p 6379:6379 redis:latest
```

**Linux (Ubuntu/Debian)**:

```bash
sudo systemctl start redis-server
redis-cli ping   # → PONG
```

**macOS (Homebrew)**:

```bash
brew services start redis
redis-cli ping   # → PONG
```

### 2. Start the API server

```bash
uvicorn app.main:app --reload
```

The server starts at **http://127.0.0.1:8000**.

### 3. Open the interactive docs

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

---

## 🔐 Authentication & Roles

### Default Admin Account

A default admin user is created automatically during the first startup:

| Field    | Value      |
| -------- | ---------- |
| Username | `admin`    |
| Password | `admin123` |

### Roles

| Role              | Description                                                       |
| ----------------- | ----------------------------------------------------------------- |
| `admin`           | Full access — can CRUD everything                                 |
| `project_manager` | Create/update own projects, create/update tasks in owned projects |
| `employee`        | View own tasks, update task status only (on assigned tasks)       |

### Login Flow

1. `POST /api/v1/auth/register` — create an employee account
2. `POST /api/v1/auth/login` — send `username` & `password` as form data → receive a JWT `access_token`
3. Include the token in subsequent requests: `Authorization: Bearer <token>`

---

## 📡 API Endpoints

### Health & Diagnostics

| Method | Endpoint      | Description                                    |
| ------ | ------------- | ---------------------------------------------- |
| `GET`  | `/`           | Health check                                   |
| `GET`  | `/test-email` | Send a test email to verify SMTP configuration |

### Authentication (`/api/v1/auth`)

| Method | Endpoint    | Description                                     | Auth   |
| ------ | ----------- | ----------------------------------------------- | ------ |
| `POST` | `/register` | Register a new employee                         | —      |
| `POST` | `/login`    | Obtain JWT token (form: `username`, `password`) | —      |
| `GET`  | `/me`       | Current user info                               | 🔒 Any |

### Users (`/api/v1/users`)

| Method   | Endpoint     | Description       | Auth     |
| -------- | ------------ | ----------------- | -------- |
| `GET`    | `/me`        | Current user info | 🔒 Any   |
| `DELETE` | `/{user_id}` | Delete a user     | 🔒 Admin |

### Projects v1 (`/api/v1/projects`)

| Method   | Endpoint | Description       | Auth   |
| -------- | -------- | ----------------- | ------ |
| `POST`   | `/`      | Create project    | 🔒 Any |
| `GET`    | `/`      | List all projects | 🔒 Any |
| `GET`    | `/{id}`  | Get project by ID | 🔒 Any |
| `PUT`    | `/{id}`  | Update project    | 🔒 Any |
| `DELETE` | `/{id}`  | Delete project    | 🔒 Any |

### Tasks v1 (`/api/v1/tasks`)

| Method   | Endpoint | Description    | Auth   |
| -------- | -------- | -------------- | ------ |
| `POST`   | `/`      | Create task    | 🔒 Any |
| `GET`    | `/`      | List all tasks | 🔒 Any |
| `GET`    | `/{id}`  | Get task by ID | 🔒 Any |
| `PUT`    | `/{id}`  | Update task    | 🔒 Any |
| `DELETE` | `/{id}`  | Delete task    | 🔒 Any |

### Projects v2 — Role-Gated (`/api/v1/v2/projects`)

| Method   | Endpoint | Description       | Auth                 |
| -------- | -------- | ----------------- | -------------------- |
| `POST`   | `/`      | Create project    | 🔒 Admin, PM         |
| `GET`    | `/`      | List all projects | 🔒 Any               |
| `GET`    | `/{id}`  | Get project by ID | 🔒 Any               |
| `PUT`    | `/{id}`  | Update project    | 🔒 Admin, PM (owner) |
| `DELETE` | `/{id}`  | Delete project    | 🔒 Admin             |

### Tasks v2 — Role-Gated (`/api/v1/v2/tasks`)

| Method   | Endpoint | Description                            | Auth         |
| -------- | -------- | -------------------------------------- | ------------ |
| `POST`   | `/`      | Create task                            | 🔒 Admin, PM |
| `GET`    | `/`      | List tasks (filterable, role-scoped)   | 🔒 Any       |
| `GET`    | `/{id}`  | Get task by ID (role-scoped)           | 🔒 Any       |
| `PATCH`  | `/{id}`  | Update task (field-restricted by role) | 🔒 Any       |
| `DELETE` | `/{id}`  | Delete task                            | 🔒 Admin     |

**Task Filters** (GET `/api/v1/v2/tasks/`):

| Query Param     | Values                        | Scope                                   |
| --------------- | ----------------------------- | --------------------------------------- |
| `?status=`      | `todo`, `in_progress`, `done` | All roles                               |
| `?priority=`    | `low`, `medium`, `high`       | All roles                               |
| `?assignee_id=` | User ID                       | Admin / PM only (ignored for employees) |

---

## 🔄 Task Status Lifecycle

All status transitions are validated — invalid transitions return **HTTP 422**.

```
todo  ──►  in_progress  ──►  done
              ◄──                ◄──
```

| From          | Allowed Transitions           |
| ------------- | ----------------------------- |
| `todo`        | → `in_progress`               |
| `in_progress` | → `done`, → `todo` (rollback) |
| `done`        | → `in_progress` (reopen)      |

New tasks **must** start with status `todo`.

---

## 🛡️ Role Permission Matrix (v2 Endpoints)

| Action                    |  Admin   |  Project Manager  |    Employee    |
| ------------------------- | :------: | :---------------: | :------------: |
| Create project            |    ✅    |        ✅         |       ❌       |
| Read projects             |    ✅    |        ✅         |       ✅       |
| Update project            |    ✅    |   ✅ (own only)   |       ❌       |
| Delete project            |    ✅    |        ❌         |       ❌       |
| Create task               |    ✅    |        ✅         |       ❌       |
| Read tasks                | ✅ (all) | ✅ (own projects) | ✅ (own tasks) |
| Update task — any field   |    ✅    |        ✅         |       ❌       |
| Update task — status only |    ✅    |        ✅         | ✅ (own task)  |
| Delete task               |    ✅    |        ❌         |       ❌       |

---

## 📝 Logging System

The project uses **Loguru** for structured, colourful logging with a custom ASGI middleware.

### Terminal Output

Clean, professional logs with a custom format. Every line includes a `req={uuid}` field to correlate all logs for a single request.

```
2026-05-03 06:08:27.903 | INFO     | app.main:lifespan:18 | req=- | Task Management API starting up — all systems go
2026-05-03 06:08:27.904 | INFO     | uvicorn.error:startup:62 | req=- | Application startup complete.
2026-05-03 05:52:21.202 | INFO     | app.core.middleware:__call__:32 | req=a1b2c3d4 | [REQUEST]  POST /api/v1/auth/login
2026-05-03 05:52:21.236 | WARNING  | app.api.auth_api:login:54 | req=a1b2c3d4 | AUTH FAILED | username=fakeuser | ip=127.0.0.1 | reason=user_not_found
2026-05-03 05:52:23.738 | SUCCESS  | app.services.email_service:_send:104 | req=a1b2c3d4 | EMAIL SENT | to=admin@example.com
2026-05-03 05:52:23.744 | WARNING  | app.core.middleware:__call__:65 | req=a1b2c3d4 | [RESPONSE] POST /api/v1/auth/login | status=401 | 2541.47ms
```

| Level    | Colour     | Use Case                                            |
| -------- | ---------- | --------------------------------------------------- |
| TRACE    | —          | Very verbose debugging                              |
| DEBUG    | Blue       | Internal state inspection                           |
| INFO     | Green      | Normal operations (requests, responses, email sent) |
| SUCCESS  | Bold green | Confirmed completions (email delivered)             |
| WARNING  | Yellow     | Auth failures, 4xx responses, unauthorized access   |
| ERROR    | Red        | 5xx responses, SMTP failures                        |
| CRITICAL | Bold red   | Failed admin login attempts, unhandled exceptions   |

### File Sinks

| File              | Level    | Rotation | Retention |
| ----------------- | -------- | -------- | --------- |
| `logs/app.log`    | INFO+    | 10 MB    | 30 days   |
| `logs/errors.log` | WARNING+ | 5 MB     | 60 days   |

Both file sinks use ZIP compression and async writing (`enqueue=True`).
Note: `KeyboardInterrupt` (CTRL+C) exceptions are filtered out of file sinks to prevent clutter, but remain visible in the terminal.

### Middleware

Every HTTP request/response is logged automatically by `LoggingMiddleware` with:

- HTTP method & path
- Client IP address
- Response status code
- Response time (milliseconds)
- An `X-Response-Time` header injected into every response

---

## 📧 Email Security Alerts

The system sends **real-time email notifications** for security-sensitive events via SMTP.

### Triggers

| Event                             | Email Subject                                  | When                                            |
| --------------------------------- | ---------------------------------------------- | ----------------------------------------------- |
| **Failed login — user not found** | 🔒 Security Alert: Failed Login Attempt        | Any login attempt with a non-existent username  |
| **Failed login — wrong password** | 🔒 Security Alert: Failed Login Attempt        | Wrong password for any role (admin/PM/employee) |
| **Unauthorized access**           | 🔒 Security Alert: Unauthorized Access Attempt | Accessing an endpoint without the required role |

### How It Works

- Emails are dispatched asynchronously via FastAPI's `BackgroundTasks` to avoid blocking the HTTP response (minimizing latency).
- Security alert logs (like `[CRITICAL]` for failed admin logins) are fired synchronously _before_ the response returns.
- Uses `smtplib` with STARTTLS and a proper SSL context.
- All send attempts (success or failure) are logged in the terminal as background events with the matching `request_id`.

**Implementation Details:**

- **Preventing Task Drops:** When a login fails, the API returns a custom `JSONResponse(status_code=401, background=background_tasks)` instead of raising an `HTTPException`. This prevents FastAPI's default exception handler from discarding the queued background tasks.
- **Bulletproof Execution:** The background email functions are wrapped in a robust `try/except` block with `logger.exception()` to ensure any unexpected errors during background execution are explicitly logged and never fail silently.

### Verify SMTP Configuration

Hit the diagnostic endpoint to verify your email setup works:

```
GET /test-email
```

**Success**: `{"status": "ok", "message": "Test email sent successfully. Check your inbox."}`
**Failure**: `{"status": "error", "message": "Email failed — check the terminal logs for details."}`

---

## 🗄️ Caching System

Uses **Redis** with a Cache-Aside pattern and automatic TTL expiration.

### Cache Configuration

| Setting             | Default       | Description                |
| ------------------- | ------------- | -------------------------- |
| `CACHE_USER_TTL`    | 300s (5 min)  | Authenticated user lookups |
| `CACHE_PROJECT_TTL` | 600s (10 min) | Project lookups & list     |
| `CACHE_TASK_TTL`    | 300s (5 min)  | Reserved for future use    |

### What Gets Cached

- ✅ User lookups by ID (during token validation)
- ✅ Project by ID (single fetch)
- ✅ All projects list (`GET /api/v1/projects`)
- ✅ Project existence checks (during task creation)

### Automatic Invalidation

Cache is cleared when:

- A new project is created
- A project is updated or deleted
- A task is created, updated, or deleted (project cache affected)

### Monitor Cache Operations

```bash
redis-cli MONITOR
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_auth.py -v
```

Tests use an **in-memory SQLite** database and a separate FastAPI `TestClient` — no external services required.

---

## 🗃️ Database

The project uses **SQLite** by default (file: `task_management.db`).

### Inspect the Database

```bash
# Windows (if sqlite3 is in PATH)
sqlite3 task_management.db

# Linux/macOS
sqlite3 task_management.db
```

Common queries:

```sql
.tables                           -- list all tables
SELECT * FROM users;              -- view all users
SELECT * FROM projects;           -- view all projects
SELECT * FROM tasks;              -- view all tasks
.quit                             -- exit
```

---

## 📦 Dependencies

| Package                          | Purpose                                    |
| -------------------------------- | ------------------------------------------ |
| `fastapi`                        | Web framework                              |
| `uvicorn`                        | ASGI server                                |
| `sqlalchemy`                     | ORM & database                             |
| `python-jose`                    | JWT token encoding/decoding                |
| `bcrypt`                         | Password hashing                           |
| `python-multipart`               | Form data parsing (login)                  |
| `pydantic` / `pydantic-settings` | Request/response validation & .env loading |
| `email-validator`                | Email field validation                     |
| `redis`                          | Cache client                               |
| `loguru`                         | Structured logging                         |
| `pytest` / `httpx`               | Testing                                    |

---

## 📄 License

This project is developed for academic purposes as part of a university course.

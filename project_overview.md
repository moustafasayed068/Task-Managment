# Task Management Project Overview

This document provides a comprehensive, detailed breakdown of the Task Management project. It covers the project structure, what each file does, the underlying logic and methods, and the libraries used.

## 1. Technologies & Libraries Used

### Backend Stack

- **FastAPI:** A modern, high-performance web framework for building APIs with Python. It provides automatic documentation (Swagger) and fast execution.
- **SQLAlchemy:** The Python SQL toolkit and Object-Relational Mapper (ORM). Used for interacting with the SQLite database via Python objects.
- **Pydantic:** Used for data validation and settings management using Python type annotations (schemas).
- **SQLite:** A lightweight, disk-based database. It is configured to use Write-Ahead Logging (WAL) for better concurrency.
- **Redis:** An in-memory data structure store, used here as a caching layer to improve read performance.
- **Uvicorn:** An ASGI web server implementation for Python, used to run the FastAPI application.
- **Bcrypt & Python-Jose:** Used for password hashing and generating/verifying JWT (JSON Web Tokens) for authentication.
- **Loguru:** A third-party logging library used for enhanced, structured logging.

### Frontend Stack

- **Vanilla HTML/CSS/JavaScript:** No heavy frameworks (like React or Vue) are used. The application relies on standard HTML for structure, CSS for styling, and Vanilla JS for DOM manipulation and API communication via the `fetch` API.

### Infrastructure

- **Docker & Docker Compose:** Containerizes the FastAPI backend and Redis service for isolated and consistent deployment environments.

---

## 2. Project Structure Breakdown

The project follows a modular, layered architecture, separating routing, business logic, and database operations.

```text
c:\Uni\Semester 6\R and Py\Task-Managment1\
├── .env                    # Environment variables (e.g., secrets, DB URLs, Redis config)
├── docker-compose.yml      # Orchestrates the Python app and Redis containers
├── Dockerfile              # Instructions to build the Python app container image
├── requirements.txt        # Python package dependencies
├── Frontend/               # Static frontend files
│   ├── index.html          # Main user interface
│   ├── monitoring.html     # Dashboard for system health and logs
│   ├── script.js           # Frontend logic and API calls
│   └── style.css           # Styling
└── app/                    # Backend source code root
    ├── main.py             # FastAPI entry point
    ├── dependencies_app.py # Shared dependency injections
    ├── api/                # API Routers (Controllers)
    ├── core/               # Core configuration, security, and utilities
    ├── db/                 # Database connection and session management
    ├── models/             # SQLAlchemy ORM models (Database tables)
    ├── schemas/            # Pydantic models (Data validation)
    └── services/           # Business logic layer
```

---

## 3. Detailed File & Module Explanations

### `app/main.py`

**Purpose:** The entry point of the FastAPI application.

- **Logic:**
  - Initializes the FastAPI app instance.
  - Uses a `lifespan` context manager to run startup tasks: creating database tables, seeding a default admin user, and checking the Redis connection.
  - Adds global middlewares: `CORSMiddleware` (for frontend-backend communication), `LoggingMiddleware`, and `MonitoringMiddleware` (tracks request stats).
  - Includes all API routers from `app/api/router_api.py`.
  - Defines a `/monitoring` sub-router to serve health checks and recent logs.

### `app/api/` (Controllers/Routers)

**Purpose:** Defines the HTTP endpoints (GET, POST, PUT, DELETE). They receive requests, validate data (via Schemas), call the Service layer, and return responses.

- **`tasks_api.py` / `projects_api.py` / `users_api.py`:** Handles CRUD operations for their respective entities.
  - _Methods:_ `create_task`, `get_tasks`, `update_task`, `delete_task`.
  - _Logic:_ They rely heavily on FastAPI `Depends()` to inject the current user (for authorization) and the database session. They also utilize caching decorators to speed up repetitive reads.
- **`auth_api.py`:** Handles user registration, login (issuing JWTs), and retrieving the current user's profile.

### `app/services/` (Business Logic)

**Purpose:** Contains the core rules of the application. The API layer delegates work here.

- **`task_service.py`:**
  - _Logic:_ Enforces Role-Based Access Control (RBAC). For example, an `employee` can only update the status of their own tasks, while a `project_manager` can manage tasks within their own projects.
  - _Methods:_ Validates state transitions (e.g., a task can go from `todo` to `in_progress`). Handles the actual database insertion/updating using SQLAlchemy.
- **`project_service.py`:** Similar to tasks, handles the creation and assignment of projects, ensuring only admins or designated PMs can manage them.

### `app/models/` (Database Models)

**Purpose:** Defines the SQLAlchemy ORM classes that map directly to SQLite tables.

- **`task_models.py`:** Defines the `TaskModel` with columns like `id`, `title`, `description`, `status` (todo, in_progress, done), `priority`, and foreign keys linking to `projects.id` and `users.id`.
- **`project_models.py` & `user_models.py`:** Define the `Project` and `User` entities, including roles (`admin`, `project_manager`, `employee`).

### `app/schemas/` (Pydantic Schemas)

**Purpose:** Defines how data should look when coming in (requests) and going out (responses).

- **Logic:** If a frontend sends a request to create a task, Pydantic ensures `title` is a string and `project_id` is an integer before the code even runs. If the data is invalid, FastAPI automatically returns a 422 Error.

### `app/core/` (Core Utilities)

**Purpose:** System-wide configurations, security, caching, and logging.

- **`security.py`:** Contains methods to hash passwords (`hash_password`) and verify them, as well as functions to generate and decode JWT access tokens.
- **`cache_core.py`:** A highly resilient caching module.
  - _Logic:_ Uses a "Circuit Breaker" pattern. It attempts to connect to Redis. If Redis is down or unavailable, it gracefully falls back to an in-memory dictionary cache (`_mem_cache`).
  - _Methods:_ Exposes decorators like `@cache_project_by_id` which intercept function calls. If the data is in the cache, it returns it instantly; otherwise, it hits the database, caches the result, and returns it.
- **`middleware.py` & `monitoring_middleware.py`:** Intercept incoming requests and outgoing responses to log the duration, status codes, and update an in-memory statistics counter (uptime, total requests, total errors).

### `app/db/` (Database Setup)

- **`session_db.py`:**
  - _Logic:_ Initializes the SQLAlchemy engine. Crucially, it uses an event listener on connect to set `PRAGMA journal_mode=WAL` (Write-Ahead Logging). This optimization allows SQLite to handle concurrent reads and writes much better, preventing database lockups under load.
  - _Methods:_ Provides the `get_db()` dependency which yields a database session for a request and closes it afterward.

### `Frontend/` (Client Side)

- **`index.html`:** Contains the structural markup for login/registration forms and the main dashboard (Projects and Tasks views).
- **`script.js`:**
  - _Logic:_ Manages the application state (`token`, `currentUser`, `isLoginMode`).
  - _Methods:_
    - `login()` / `register()`: Sends credentials to the backend. Stores the JWT token.
    - `loadProjectsAndTasks()`: Fetches data using the `Authorization: Bearer <token>` header. It dynamically generates HTML to render projects and their nested tasks based on the user's role (hiding admin controls for employees).
    - DOM events trigger actions like `createProject()`, `submitTaskModal()`, and `updateTaskStatus()`.

---

## 4. Key Workflows

1.  **Authentication Flow:**
    - User enters credentials in `index.html`.
    - `script.js` sends a POST to `/api/v1/auth/login`.
    - FastAPI routes the request to `auth_api.py`.
    - It checks the DB, verifies the hash using `security.py`, and returns a JWT.
    - Frontend stores the JWT and attaches it to subsequent requests.
2.  **Creating a Task:**
    - PM clicks "Add Task", filling out the modal.
    - `script.js` sends POST to `/api/v1/v2/tasks/`.
    - `tasks_api.py` receives it. The `Depends(get_current_user)` middleware decodes the JWT and verifies the user is valid.
    - The `create_task` router calls `cache_core` to quickly verify the `project_id` and `assignee_id` exist.
    - The database writes the new task, and `invalidate_project_cache()` is called so the next GET request fetches fresh data.
    - Response is returned, and the frontend re-renders the DOM.

This architecture ensures a clean separation of concerns, fast response times (via Redis/In-memory caching), safe concurrent database operations (via WAL), and strict role-based security.

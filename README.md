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
cd Image-captioning
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the App

```bash
uvicorn app.main:app --reload
```

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

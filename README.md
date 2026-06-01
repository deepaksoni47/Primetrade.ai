# PrimeTrade Backend Assignment

PrimeTrade is a FastAPI backend assignment with PostgreSQL, JWT authentication, refresh-token cookies, task CRUD, Redis-backed rate limiting and caching, audit logs, Swagger docs, Docker, and a small browser-based frontend for testing the API.

## What This Project Does

- Lets a user register, log in, refresh a session, and log out.
- Stores users and tasks in PostgreSQL.
- Protects task and admin routes with JWT authentication and role-based access control.
- Shows live API documentation with Swagger at `/docs`.
- Serves a frontend at `/` so the app can be tried without a separate client.
- Uses Redis for rate limiting and short-lived cache entries.
- Records audit logs for important actions.
- Includes Docker Compose so the full stack can be started locally.

## Tech Stack

- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Alembic migrations
- JWT access tokens and refresh-token cookies
- Redis
- Pydantic validation
- HTTPX external API integration
- Pytest
- Docker and Docker Compose

## Project URLs

When the app is running locally or in Docker:

- Frontend: `http://localhost:8000/`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

## Quick Start

1. Copy `.env.example` to `.env`.
2. Update the secret values if needed.
3. Install dependencies with `pip install -r requirements.txt`.
4. Start PostgreSQL and Redis, or use Docker Compose.
5. Run the app with `uvicorn app.main:app --reload`.
6. Open `http://localhost:8000/` in your browser.

## Docker

The easiest way to run the complete stack is:

```bash
docker compose up --build
```

This starts:

- `api` on port `8000`
- PostgreSQL on port `5432`
- Redis on port `6379`

The Docker setup creates the schema automatically on startup and seeds an admin user using the values from the environment file.

## Default Login

If you use the default Docker environment values from `.env.example`, the seeded admin account is:

- Email: `admin@example.com`
- Password: `Admin12345!`

You can log in with that account from the frontend to view the admin user list.

## Frontend Guide

The frontend is a lightweight dashboard served by FastAPI itself, not a separate SPA build.

From the UI you can:

- Register or log in
- View your current session
- Create, edit, search, and delete tasks
- Refresh the list of tasks
- Load the admin user list when signed in as an admin

The frontend uses the same API at `/api/v1`, stores the access token in session storage, and relies on the refresh-token cookie for session renewal.

## API Overview

Auth routes:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

Task routes:

- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `PUT /api/v1/tasks/{task_id}`
- `DELETE /api/v1/tasks/{task_id}`

Admin routes:

- `GET /api/v1/admin/users`

External integration:

- `GET /api/v1/external/btc-price`

## Configuration

The main settings live in `.env` and are documented in `.env.example`.

Important values:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT signing secret
- `ACCESS_TOKEN_EXPIRE_MINUTES`: access token lifetime
- `REFRESH_TOKEN_EXPIRE_DAYS`: refresh token lifetime
- `SECURE_REFRESH_COOKIE`: set `true` in HTTPS production deployments
- `AUTO_CREATE_SCHEMA`: create tables on startup
- `SEED_ADMIN_EMAIL`: admin email used on startup
- `SEED_ADMIN_PASSWORD`: admin password used on startup
- `RATE_LIMIT_REQUESTS_PER_MINUTE`: request cap for API routes
- `CACHE_TTL_SECONDS`: Redis cache duration
- `EXTERNAL_API_TIMEOUT_SECONDS`: timeout for the BTC price request
- `EXTERNAL_API_RETRY_ATTEMPTS`: retry count for the external request

## Testing

Run the full test suite with:

```bash
pytest -q
```

The tests cover:

- Authentication
- Task CRUD
- Redis-backed caching
- Rate limiting
- Audit logging
- External API failure handling

## Database Migrations

If you need to apply Alembic migrations manually, use the normal Alembic workflow for the repository. The initial schema includes users, tasks, refresh-token sessions, and audit logs.

## Project Structure

- `app/core`: configuration, security, database, Redis, logging, caching, rate limiting
- `app/api/routes`: HTTP endpoints
- `app/models`: SQLAlchemy models
- `app/schemas`: Pydantic request and response models
- `app/services`: external integrations and service helpers
- `frontend`: browser UI served by the backend
- `alembic`: database migrations
- `tests`: automated test coverage

## Troubleshooting

- If the frontend does not load, check that the API is running on port `8000`.
- If database calls fail in Docker, confirm PostgreSQL is healthy and the `DATABASE_URL` matches the Compose service name.
- If Redis features are disabled, verify that the Redis container is healthy and `REDIS_URL` is set correctly.
- If you see an external BTC price `503`, the upstream service was unreachable or timed out; the app now handles that gracefully.

## Notes

- Swagger docs are the live API reference for request and response shapes.
- The frontend is intentionally minimal and exists to demonstrate the backend workflows quickly.
- The app exposes a single-page style UI at `/`, so first-time visitors can try the API without using Postman.

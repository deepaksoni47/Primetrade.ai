import logging
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from app.api.routes.external import router as external_router
from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.tasks import router as tasks_router
from app.core.config import Settings, get_settings
from app.core.database import Base, create_db_engine, create_session_factory
from app.core.rate_limit import build_rate_limit_key, rate_limit_response
from app.core.redis_client import create_redis_client, redis_connection_is_ready
from app.core.logging import configure_logging
from app.core.security import decode_token, hash_password
from app.models.audit_log import AuditLog
from app.models import User
from app.models.user import UserRole


logger = logging.getLogger(__name__)


def build_frontend_paths() -> tuple[Path, Path]:
    root_dir = Path(__file__).resolve().parents[1]
    frontend_dir = root_dir / "frontend"
    return root_dir, frontend_dir


def seed_admin_user(session, settings: Settings) -> None:
    if not settings.seed_admin_email or not settings.seed_admin_password:
        return

    existing_admin = session.scalar(select(User).where(User.email == settings.seed_admin_email.lower().strip()))
    if existing_admin is not None:
        return

    admin = User(
        email=settings.seed_admin_email.lower().strip(),
        full_name="Admin User",
        hashed_password=hash_password(settings.seed_admin_password),
        role=UserRole.admin.value,
    )
    session.add(admin)
    session.commit()


def extract_actor_context(request: Request, settings: Settings) -> tuple[str | None, str | None]:
    authorization = request.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token, secret_key=settings.secret_key, algorithm=settings.algorithm)
            if payload.get("type") == "access":
                return payload.get("sub"), payload.get("role")
        except Exception:  # noqa: BLE001
            pass

    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            payload = decode_token(refresh_token, secret_key=settings.secret_key, algorithm=settings.algorithm)
            if payload.get("type") == "refresh":
                return payload.get("sub"), payload.get("role")
        except Exception:  # noqa: BLE001
            pass

    return None, None


def should_audit(request: Request, status_code: int) -> bool:
    if request.url.path.startswith("/static") or request.url.path == "/health":
        return False
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        return True
    return request.url.path.startswith("/api/v1/auth") and status_code < 500


def resource_identifier(path: str) -> str | None:
    parts = [part for part in path.split("/") if part]
    if not parts:
        return None
    tail = parts[-1]
    if tail in {"register", "login", "refresh", "logout", "me", "users", "btc-price"}:
        return None
    return tail


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    resolved_settings = settings or get_settings()
    engine = create_db_engine(resolved_settings.database_url)
    session_factory = create_session_factory(engine)
    _, frontend_dir = build_frontend_paths()
    redis_client = create_redis_client(resolved_settings.redis_url)
    if not redis_connection_is_ready(redis_client):
        redis_client = None

    app = FastAPI(title=resolved_settings.app_name, version="1.0.0")
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.SessionLocal = session_factory
    app.state.redis = redis_client

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir), html=False), name="static")

    @app.on_event("startup")
    def startup() -> None:
        if resolved_settings.auto_create_schema:
            Base.metadata.create_all(bind=engine)
            try:
                with session_factory() as session:
                    session.execute(text("ALTER TABLE audit_logs ALTER COLUMN action TYPE VARCHAR(255);"))
                    session.commit()
            except Exception as e:
                logger.warning("Failed to alter audit_logs table: %s", e)
            with session_factory() as session:
                seed_admin_user(session, resolved_settings)

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_settings = request.app.state.settings
        if request.url.path.startswith("/api/") and request.url.path not in {"/api/openapi.json", "/api/docs"}:
            redis_client = request.app.state.redis
            if redis_client is not None:
                key = build_rate_limit_key(request)
                current_count = redis_client.incr(key)
                if current_count == 1:
                    redis_client.expire(key, 60)
                if current_count > request_settings.rate_limit_requests_per_minute:
                    return rate_limit_response(request_settings.rate_limit_requests_per_minute)

        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request failure")
            raise
        elapsed_ms = (perf_counter() - start) * 1000
        logger.info("%s %s -> %s in %.2fms", request.method, request.url.path, response.status_code, elapsed_ms)

        if should_audit(request, response.status_code):
            actor_user_id, actor_role = extract_actor_context(request, resolved_settings)
            with session_factory() as session:
                session.add(
                    AuditLog(
                        actor_user_id=actor_user_id,
                        actor_role=actor_role,
                        action=f"{request.method} {request.url.path}"[:255],
                        resource=request.url.path,
                        resource_id=resource_identifier(request.url.path),
                        status_code=response.status_code,
                        client_ip=request.client.host if request.client else None,
                    )
                )
                session.commit()

        return response

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": exc.errors()})

    @app.exception_handler(Exception)
    async def generic_handler(_: Request, exc: Exception):
        logger.exception("Unexpected server error", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.get("/", include_in_schema=False)
    def frontend() -> FileResponse:
        index_file = frontend_dir / "index.html"
        if not index_file.exists():
            return JSONResponse(status_code=404, content={"detail": "Frontend not found"})
        return FileResponse(index_file)

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router, prefix=f"{resolved_settings.api_v1_prefix}/auth", tags=["auth"])
    app.include_router(tasks_router, prefix=f"{resolved_settings.api_v1_prefix}/tasks", tags=["tasks"])
    app.include_router(admin_router, prefix=f"{resolved_settings.api_v1_prefix}/admin", tags=["admin"])
    app.include_router(external_router, prefix=f"{resolved_settings.api_v1_prefix}/external", tags=["external"])

    return app


app = create_app()

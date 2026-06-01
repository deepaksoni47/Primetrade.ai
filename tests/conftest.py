from pathlib import Path
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


class FakeRedis:
    def __init__(self):
        self.store: dict[str, tuple[str, float | None]] = {}

    def ping(self) -> bool:
        return True

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [key for key, (_, expires_at) in self.store.items() if expires_at is not None and expires_at <= now]
        for key in expired:
            self.store.pop(key, None)

    def get(self, key: str):
        self._purge_expired()
        item = self.store.get(key)
        return None if item is None else item[0]

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.store[key] = (value, time.time() + ttl_seconds)

    def incr(self, key: str) -> int:
        self._purge_expired()
        current, expires_at = self.store.get(key, ("0", None))
        next_value = int(current) + 1
        self.store[key] = (str(next_value), expires_at)
        return next_value

    def expire(self, key: str, ttl_seconds: int) -> None:
        self._purge_expired()
        current = self.store.get(key)
        if current is None:
            return
        self.store[key] = (current[0], time.time() + ttl_seconds)

    def delete(self, *keys: str) -> None:
        for key in keys:
            self.store.pop(key, None)

    def scan(self, cursor: int = 0, match: str = "*", count: int = 100):
        self._purge_expired()
        prefix = match.rstrip("*")
        keys = [key for key in self.store if key.startswith(prefix)]
        return 0, keys


@pytest.fixture()
def app(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'test.db').as_posix()}"
    settings = Settings(
        database_url=database_url,
        secret_key="test-secret",
        auto_create_schema=True,
        secure_refresh_cookie=False,
        seed_admin_email=None,
        seed_admin_password=None,
    )
    application = create_app(settings)
    application.state.redis = FakeRedis()
    return application


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "full_name": "Test User", "password": "Password123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

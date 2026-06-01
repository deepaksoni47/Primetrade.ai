from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.user import User


def test_external_api_response_is_cached(client, app, monkeypatch):
    def fake_fetch_btc_price(*, timeout_seconds, attempts):
        return {
            "source": "coindesk",
            "updated_at": "2026-06-01T00:00:00Z",
            "currency": "USD",
            "rate": "100000.00",
            "description": "Bitcoin",
            "attempt": 1,
        }

    monkeypatch.setattr("app.api.routes.external.fetch_btc_price", fake_fetch_btc_price)

    first = client.get("/api/v1/external/btc-price")
    second = client.get("/api/v1/external/btc-price")

    assert first.status_code == 200
    assert first.json()["cached"] is False
    assert second.status_code == 200
    assert second.json()["cached"] is True


def test_external_api_failure_returns_503(client, monkeypatch):
    def failing_fetch_btc_price(*, timeout_seconds, attempts):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.api.routes.external.fetch_btc_price", failing_fetch_btc_price)

    response = client.get("/api/v1/external/btc-price")

    assert response.status_code == 503
    assert response.json()["detail"] == "External BTC price service is unavailable"


def test_rate_limit_blocks_repeated_requests(client, app, monkeypatch):
    app.state.settings.rate_limit_requests_per_minute = 1

    def fake_fetch_btc_price(*, timeout_seconds, attempts):
        return {
            "source": "coindesk",
            "updated_at": "2026-06-01T00:00:00Z",
            "currency": "USD",
            "rate": "100000.00",
            "description": "Bitcoin",
            "attempt": 1,
        }

    monkeypatch.setattr("app.api.routes.external.fetch_btc_price", fake_fetch_btc_price)

    first = client.get("/api/v1/external/btc-price")
    second = client.get("/api/v1/external/btc-price")

    assert first.status_code == 200
    assert second.status_code == 429


def test_audit_log_written_for_task_creation(client, app, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.external.fetch_btc_price",
        lambda **kwargs: {
            "source": "coindesk",
            "updated_at": "2026-06-01T00:00:00Z",
            "currency": "USD",
            "rate": "100000.00",
            "description": "Bitcoin",
            "attempt": 1,
        },
    )

    session_factory = app.state.SessionLocal
    with session_factory() as session:
        session.add(
            User(
                email="owner@example.com",
                full_name="Owner User",
                hashed_password=hash_password("Password123!"),
                role="user",
            )
        )
        session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]

    create = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Audit me", "description": "Track this action", "status": "pending"},
    )
    assert create.status_code == 201

    with session_factory() as session:
        logs = session.query(AuditLog).all()
        assert any(log.action == "POST /api/v1/tasks" for log in logs)
        assert any(log.actor_user_id is not None for log in logs)

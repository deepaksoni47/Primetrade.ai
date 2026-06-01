from app.core.security import hash_password
from app.models.user import User


def test_register_login_and_me(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "jane@example.com", "full_name": "Jane Doe", "password": "Password123!"},
    )
    assert register.status_code == 201
    body = register.json()
    assert body["access_token"]
    assert body["user"]["email"] == "jane@example.com"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "jane@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "jane@example.com"


def test_duplicate_registration_is_rejected(client):
    payload = {"email": "dup@example.com", "full_name": "Dup User", "password": "Password123!"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409


def test_admin_users_endpoint_requires_admin(client, app):
    session_factory = app.state.SessionLocal
    with session_factory() as session:
        session.add(
            User(
                email="admin@example.com",
                full_name="Admin User",
                hashed_password=hash_password("Password123!"),
                role="admin",
            )
        )
        session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    users = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert users.status_code == 200
from app.core.security import hash_password
from app.models.user import User


def test_register_login_and_me(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "jane@example.com", "full_name": "Jane Doe", "password": "Password123!"},
    )
    assert register.status_code == 201
    body = register.json()
    assert body["access_token"]
    assert body["user"]["email"] == "jane@example.com"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "jane@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "jane@example.com"


def test_duplicate_registration_is_rejected(client):
    payload = {"email": "dup@example.com", "full_name": "Dup User", "password": "Password123!"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409


def test_admin_users_endpoint_requires_admin(client, app):
    session_factory = app.state.SessionLocal
    with session_factory() as session:
        session.add(
            User(
                email="admin@example.com",
                full_name="Admin User",
                hashed_password=hash_password("Password123!"),
                role="admin",
            )
        )
        session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    users = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert users.status_code == 200

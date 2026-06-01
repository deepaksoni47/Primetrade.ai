from app.core.security import hash_password
from app.models.user import User


def test_task_crud_and_filtering(client, app):
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
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"title": "Ship demo", "description": "Create assignment demo", "status": "pending"},
    )
    assert create.status_code == 201
    task_id = create.json()["id"]

    listing = client.get("/api/v1/tasks?q=Ship", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    update = client.put(
        f"/api/v1/tasks/{task_id}",
        headers=headers,
        json={"status": "completed"},
    )
    assert update.status_code == 200
    assert update.json()["status"] == "completed"

    delete = client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert delete.status_code == 204
from app.core.security import hash_password
from app.models.user import User


def test_task_crud_and_filtering(client, app):
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
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"title": "Ship demo", "description": "Create assignment demo", "status": "pending"},
    )
    assert create.status_code == 201
    task_id = create.json()["id"]

    listing = client.get("/api/v1/tasks?q=Ship", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    update = client.put(
        f"/api/v1/tasks/{task_id}",
        headers=headers,
        json={"status": "completed"},
    )
    assert update.status_code == 200
    assert update.json()["status"] == "completed"

    delete = client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert delete.status_code == 204

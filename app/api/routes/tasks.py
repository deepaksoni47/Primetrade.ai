from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_delete_prefix, cache_get_json, cache_set_json
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskListResponse, TaskRead, TaskUpdate


router = APIRouter()


def can_access_task(user: User, task: Task) -> bool:
    return user.role == "admin" or task.owner_id == user.id


def task_query_for_user(user: User):
    return select(Task) if user.role == "admin" else select(Task).where(Task.owner_id == user.id)


def build_task_cache_key(user: User, q: str | None, status_filter: TaskStatus | None, limit: int, offset: int) -> str:
    return f"tasks:list:{user.role}:{user.id}:{q or ''}:{status_filter.value if status_filter else ''}:{limit}:{offset}"


@router.get("", response_model=TaskListResponse)
def list_tasks(
    request: Request,
    q: str | None = Query(default=None, max_length=120),
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskListResponse:
    cache_client = request.app.state.redis
    cache_key = build_task_cache_key(current_user, q, status_filter, limit, offset)
    cached = cache_get_json(cache_client, cache_key)
    if cached is not None:
        return TaskListResponse(**cached)

    query = task_query_for_user(current_user)
    if q:
        search_term = f"%{q.strip()}%"
        query = query.where((Task.title.ilike(search_term)) | (Task.description.ilike(search_term)))
    if status_filter:
        query = query.where(Task.status == status_filter.value)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(Task.created_at.desc()).offset(offset).limit(limit)).all()
    payload = TaskListResponse(items=[TaskRead.model_validate(row) for row in rows], total=total, limit=limit, offset=offset)
    cache_set_json(cache_client, cache_key, payload.model_dump(mode="json"), request.app.state.settings.cache_ttl_seconds)
    return payload


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    request: Request,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    task = Task(
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        status=payload.status.value,
        owner_id=current_user.id,
        completed_at=datetime.now(timezone.utc) if payload.status == TaskStatus.completed else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    cache_delete_prefix(request.app.state.redis, "tasks:list:")
    return TaskRead.model_validate(task)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    task = db.get(Task, task_id)
    if task is None or not can_access_task(current_user, task):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskRead.model_validate(task)


@router.put("/{task_id}", response_model=TaskRead)
def update_task(
    request: Request,
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    task = db.get(Task, task_id)
    if task is None or not can_access_task(current_user, task):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    data = payload.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        task.title = data["title"].strip()
    if "description" in data:
        task.description = data["description"].strip() if data["description"] else None
    if "status" in data and data["status"] is not None:
        task.status = data["status"].value
        task.completed_at = datetime.now(timezone.utc) if data["status"] == TaskStatus.completed else None

    db.commit()
    db.refresh(task)
    cache_delete_prefix(request.app.state.redis, "tasks:list:")
    return TaskRead.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    task = db.get(Task, task_id)
    if task is None or not can_access_task(current_user, task):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.delete(task)
    db.commit()
    cache_delete_prefix(request.app.state.redis, "tasks:list:")

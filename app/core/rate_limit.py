from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


def build_rate_limit_key(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    window = int(datetime.now(timezone.utc).timestamp() // 60)
    return f"rl:{client_host}:{request.url.path}:{window}"


def rate_limit_response(limit: int) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": f"Rate limit exceeded. Max {limit} requests per minute."},
    )
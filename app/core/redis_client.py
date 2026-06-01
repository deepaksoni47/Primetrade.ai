from collections.abc import Iterator

import redis


def create_redis_client(redis_url: str | None) -> redis.Redis | None:
    if not redis_url:
        return None
    return redis.Redis.from_url(redis_url, decode_responses=True)


def redis_connection_is_ready(client: redis.Redis | None) -> bool:
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:  # noqa: BLE001
        return False
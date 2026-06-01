import json

import redis


def cache_get_json(client: redis.Redis | None, key: str):
    if client is None:
        return None
    value = client.get(key)
    if value is None:
        return None
    return json.loads(value)


def cache_set_json(client: redis.Redis | None, key: str, value, ttl_seconds: int) -> None:
    if client is None:
        return
    client.setex(key, ttl_seconds, json.dumps(value, default=str))


def cache_delete_prefix(client: redis.Redis | None, prefix: str) -> None:
    if client is None:
        return
    cursor = 0
    pattern = f"{prefix}*"
    while True:
        cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            client.delete(*keys)
        if cursor == 0:
            break
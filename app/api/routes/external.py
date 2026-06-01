from fastapi import APIRouter, HTTPException, Request

from app.core.cache import cache_get_json, cache_set_json
from app.services.external_api import fetch_btc_price


router = APIRouter()


@router.get("/btc-price")
def btc_price(request: Request):
    settings = request.app.state.settings
    cache_client = request.app.state.redis
    cache_key = "external:coindesk:btc-price"
    cached = cache_get_json(cache_client, cache_key)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        payload = fetch_btc_price(
            timeout_seconds=settings.external_api_timeout_seconds,
            attempts=settings.external_api_retry_attempts,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="External BTC price service is unavailable",
        ) from exc

    cache_set_json(cache_client, cache_key, payload, settings.cache_ttl_seconds)
    return {**payload, "cached": False}
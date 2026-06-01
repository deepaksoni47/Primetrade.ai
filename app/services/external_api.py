from __future__ import annotations

import httpx


COINDESK_URL = "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"


def fetch_btc_price(*, timeout_seconds: float, attempts: int) -> dict:
    last_error: Exception | None = None
    timeout = httpx.Timeout(timeout_seconds)
    headers = {"User-Agent": "PrimeTrade-Assignment/1.0"}

    for attempt in range(1, attempts + 1):
        try:
            with httpx.Client(timeout=timeout, headers=headers) as client:
                response = client.get(COINDESK_URL)
                response.raise_for_status()
                payload = response.json()
                usd = payload["bpi"]["USD"]
                return {
                    "source": "coindesk",
                    "updated_at": payload.get("time", {}).get("updatedISO"),
                    "currency": usd.get("code", "USD"),
                    "rate": usd.get("rate"),
                    "description": usd.get("description"),
                    "attempt": attempt,
                }
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == attempts:
                break

    raise RuntimeError("External API request failed after retries") from last_error
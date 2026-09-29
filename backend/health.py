"""Readiness checks touch Postgres through PostgREST without reading user data."""
import asyncio
import logging
import os
from time import monotonic

import httpx
from fastapi import HTTPException

from config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)
_lock = asyncio.Lock()
_last_success = 0.0


async def readiness() -> dict:
    global _last_success
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise HTTPException(503, "Database is not configured")
    async with _lock:
        # Protect the database from repeated public probes, while scheduled
        # checks every six hours always perform a real database request.
        if not _last_success or monotonic() - _last_success >= 60:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.get(
                        f"{SUPABASE_URL}/rest/v1/datasets",
                        params={"select": "id", "limit": "1"},
                        headers={"apikey": SUPABASE_PUBLISHABLE_KEY},
                    )
                    response.raise_for_status()
                    # Anonymous RLS access returns []; never return any rows.
                    if not isinstance(response.json(), list):
                        raise ValueError("Unexpected database response")
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("Database readiness check failed: %s", type(exc).__name__)
                raise HTTPException(503, "Database is unavailable; check Supabase project status") from exc
            _last_success = monotonic()
    return {"status": "ok", "database": "ok", "revision": os.getenv("RENDER_GIT_COMMIT", "local")}

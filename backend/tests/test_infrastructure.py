from unittest.mock import AsyncMock, Mock

import httpx
import pandas as pd
import pytest
from fastapi import HTTPException

import health
from ai_insights import _ProviderChain
from data_io import parse_dataset
from dataset_store import DatasetCache
from query_planner import QueryPlan


def test_cache_bounds():
    cache = DatasetCache(max_entries=1)
    entry = {"dataframe": pd.DataFrame({"n": [1]})}
    cache["one"] = entry
    cache["two"] = entry
    assert list(cache) == ["two"]
    cache = DatasetCache(ttl=-1)
    cache["one"] = entry
    assert cache.get("one") is None
    cache = DatasetCache(max_bytes=1)
    cache["one"] = entry
    assert len(cache) == 0


def test_normalizes_headers_and_rejects_collisions():
    assert list(parse_dataset("a.csv", b" sales , region \n1,East\n").columns) == ["sales", "region"]
    with pytest.raises(HTTPException):
        parse_dataset("a.csv", b" sales ,sales\n1,2\n")


@pytest.mark.parametrize("content", [b"", b"column\n", b"\xff\xff"])
def test_empty_and_invalid_upload(content):
    with pytest.raises(HTTPException):
        parse_dataset("a.csv", content)


async def test_provider_fallback_on_status_failure():
    chain = object.__new__(_ProviderChain)
    expected = QueryPlan(sql="SELECT count(*) FROM data")
    error = httpx.HTTPStatusError("bad model", request=httpx.Request("GET", "https://example.com"), response=httpx.Response(404))
    chain._providers = [Mock(generate_structured=AsyncMock(side_effect=error)), Mock(generate_structured=AsyncMock(return_value=expected))]
    assert await chain.generate_structured("prompt", QueryPlan, max_tokens=768) == expected


async def test_database_readiness_success_and_cache(monkeypatch):
    monkeypatch.setattr(health, "_last_success", 0)
    monkeypatch.setattr(health, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(health, "SUPABASE_PUBLISHABLE_KEY", "public-key")
    response = httpx.Response(200, json=[], request=httpx.Request("GET", "https://example.com"))
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.get.return_value = response
    monkeypatch.setattr(health.httpx, "AsyncClient", lambda **kwargs: client)
    assert (await health.readiness())["database"] == "ok"
    assert (await health.readiness())["database"] == "ok"
    assert client.get.await_count == 1
    assert client.get.call_args.kwargs["params"] == {"select": "id", "limit": "1"}


async def test_database_readiness_failure(monkeypatch):
    monkeypatch.setattr(health, "_last_success", 0)
    monkeypatch.setattr(health, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(health, "SUPABASE_PUBLISHABLE_KEY", "public-key")
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.get.side_effect = httpx.ConnectError("unavailable")
    monkeypatch.setattr(health.httpx, "AsyncClient", lambda **kwargs: client)
    with pytest.raises(HTTPException) as exc:
        await health.readiness()
    assert exc.value.status_code == 503

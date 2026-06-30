import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from criadex.cache.cache import Cache
from criadex.cache.helpers import normalize_cache_text, stable_hash
from criadex.cache.objects.search_results import SearchResults


# In-process LRU cache 

@pytest.fixture
def cache():
    mysql_api = MagicMock()
    return Cache(mysql_api=mysql_api, max_size=2, ttl=1)


def test_cache_set_and_get(cache: Cache):
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_cache_ttl(cache: Cache):
    cache.set("key1", "value1")
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_cache_lru(cache: Cache):
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.get("key1")
    cache.set("key3", "value3")  # evicts key2

    assert cache.get("key1") == "value1"
    assert cache.get("key2") is None
    assert cache.get("key3") == "value3"


def test_cache_clear(cache: Cache):
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.clear()

    assert cache.get("key1") is None
    assert cache.get("key2") is None


# Helpers

def test_stable_hash_is_deterministic():
    assert stable_hash("a", "b", "c") == stable_hash("a", "b", "c")


def test_stable_hash_changes_with_content():
    assert stable_hash("x") != stable_hash("y")


def test_normalize_cache_text():
    assert normalize_cache_text("  Hello   World  ") == "hello world"
    assert normalize_cache_text("") == ""


#  SearchResults (Redis-backed)

def _make_search_results(redis_mock):
    pool = MagicMock()
    sr = SearchResults(pool)
    sr.redis = MagicMock(return_value=redis_mock)
    return sr


@pytest.mark.asyncio
async def test_search_results_build_key_includes_group():
    key_a = SearchResults.build_key(group_name="group-a", query="hello", top_k=5)
    key_b = SearchResults.build_key(group_name="group-b", query="hello", top_k=5)
    assert key_a != key_b
    assert key_a.startswith("group-a:")
    assert key_b.startswith("group-b:")


@pytest.mark.asyncio
async def test_search_results_build_key_normalizes_query():
    k1 = SearchResults.build_key(group_name="g", query="Hello World", top_k=1)
    k2 = SearchResults.build_key(group_name="g", query="hello world", top_k=1)
    assert k1 == k2


@pytest.mark.asyncio
async def test_search_results_set_and_get_roundtrip():
    redis_mock = AsyncMock()
    redis_mock.__aenter__ = AsyncMock(return_value=redis_mock)
    redis_mock.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    sr = SearchResults(pool)

    stored = {}

    async def fake_set(key, value, ex=None):
        stored[key] = value

    async def fake_get(key):
        return stored.get(key)

    redis_mock.set = fake_set
    redis_mock.get = fake_get

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def fake_redis_ctx():
        yield redis_mock

    sr.redis = fake_redis_ctx

    payload = {"nodes": [], "assets": [], "search_units": 1}
    await sr.set("g:abc", payload)
    result = await sr.get("g:abc")
    assert result == payload


@pytest.mark.asyncio
async def test_search_results_get_returns_none_on_miss():
    redis_mock = AsyncMock()
    redis_mock.__aenter__ = AsyncMock(return_value=redis_mock)
    redis_mock.__aexit__ = AsyncMock(return_value=False)
    redis_mock.get = AsyncMock(return_value=None)

    pool = MagicMock()
    sr = SearchResults(pool)

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def fake_redis_ctx():
        yield redis_mock

    sr.redis = fake_redis_ctx

    result = await sr.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_search_results_invalidate_group_deletes_matching_keys():
    redis_mock = AsyncMock()
    redis_mock.__aenter__ = AsyncMock(return_value=redis_mock)
    redis_mock.__aexit__ = AsyncMock(return_value=False)

    store = {
        "search:group-a:hash1": b"data1",
        "search:group-a:hash2": b"data2",
        "search:group-b:hash3": b"data3",
    }

    scan_calls = [0]

    async def fake_scan(cursor, match=None, count=200):
        if cursor == 0 and match == "search:group-a:*":
            keys = [k.encode() for k in store if k.startswith("search:group-a:")]
            return (0, keys)
        return (0, [])

    deleted = []

    async def fake_delete(*keys):
        for k in keys:
            key_str = k.decode() if isinstance(k, bytes) else k
            deleted.append(key_str)

    redis_mock.scan = fake_scan
    redis_mock.delete = fake_delete

    pool = MagicMock()
    sr = SearchResults(pool)

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def fake_redis_ctx():
        yield redis_mock

    sr.redis = fake_redis_ctx

    await sr.invalidate_group("group-a")

    assert "search:group-a:hash1" in deleted
    assert "search:group-a:hash2" in deleted
    assert "search:group-b:hash3" not in deleted


@pytest.mark.asyncio
async def test_search_results_swallows_redis_errors_on_get():
    pool = MagicMock()
    sr = SearchResults(pool)

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def broken_redis():
        raise ConnectionError("Redis unavailable")
        yield  # noqa: unreachable

    sr.redis = broken_redis

    result = await sr.get("any-key")
    assert result is None


@pytest.mark.asyncio
async def test_search_results_swallows_redis_errors_on_invalidate():
    pool = MagicMock()
    sr = SearchResults(pool)

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def broken_redis():
        raise ConnectionError("Redis unavailable")
        yield  # noqa: unreachable

    sr.redis = broken_redis

    # Should not raise
    await sr.invalidate_group("any-group")

import pytest
import time
from unittest.mock import MagicMock
from criadex.cache.cache import Cache

@pytest.fixture
def cache():
    """
    Fixture for the Cache class.
    """
    mysql_api = MagicMock()
    return Cache(mysql_api=mysql_api, max_size=2, ttl=1)

def test_cache_set_and_get(cache: Cache):
    """
    Test that the cache can set and get a value.
    """
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

def test_cache_ttl(cache: Cache):
    """
    Test that the cache expires entries after the TTL.
    """
    cache.set("key1", "value1")
    time.sleep(1.1)
    assert cache.get("key1") is None

def test_cache_lru(cache: Cache):
    """
    Test that the cache evicts the least recently used entry.
    """
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.get("key1") # Access key1 to make it the most recently used
    cache.set("key3", "value3") # This should evict key2

    assert cache.get("key1") == "value1"
    assert cache.get("key2") is None
    assert cache.get("key3") == "value3"

def test_cache_clear(cache: Cache):
    """
    Test that the cache can be cleared.
    """
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.clear()

    assert cache.get("key1") is None
    assert cache.get("key2") is None

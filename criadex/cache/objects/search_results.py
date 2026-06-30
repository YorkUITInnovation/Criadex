"""
Redis cache for Criadex vector-search results.

Key structure: ``search:{group_name}:{sha256(query, top_k)}``
Invalidation:  ``invalidate_group(group_name)`` — SCAN-deletes all keys for that group.

@author Kiarash Bashokian
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from criadex.cache.core import CacheObject
from criadex.cache.helpers import dumps_json, loads_json, normalize_cache_text, stable_hash

logger = logging.getLogger(__name__)


def _parse_int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


SEARCH_CACHE_TTL_SECONDS: int = _parse_int_env("SEARCH_CACHE_TTL_SECONDS", 300)


class SearchResults(CacheObject):
    """Caches ``bot.search()`` ``IndexResponse`` payloads per group + query."""

    key_prefix = "search:"

    @staticmethod
    def build_key(*, group_name: str, query: str, top_k: int) -> str:
        query_hash = stable_hash(normalize_cache_text(query), str(top_k))
        return f"{group_name}:{query_hash}"

    async def set(self, cache_key: str, result: Any, **kwargs) -> None:
        ttl = kwargs.get("ex", SEARCH_CACHE_TTL_SECONDS)
        try:
            if hasattr(result, "model_dump"):
                payload = result.model_dump(mode="json")
            else:
                payload = result
            async with self.redis() as redis:
                await redis.set(self._key(cache_key), dumps_json(payload), ex=ttl)
        except Exception as exc:
            logger.debug("search cache set failed: %s", exc)

    async def get(self, cache_key: str, **kwargs) -> Optional[Any]:
        try:
            async with self.redis() as redis:
                raw = await redis.get(self._key(cache_key))
            if raw is None:
                return None
            return loads_json(raw)
        except Exception as exc:
            logger.debug("search cache get failed: %s", exc)
            return None

    async def delete(self, cache_key: str, **kwargs) -> None:
        try:
            async with self.redis() as redis:
                await redis.delete(self._key(cache_key))
        except Exception as exc:
            logger.debug("search cache delete failed: %s", exc)

    async def exists(self, cache_key: str, **kwargs) -> bool:
        try:
            async with self.redis() as redis:
                return bool(await redis.exists(self._key(cache_key)))
        except Exception as exc:
            logger.debug("search cache exists failed: %s", exc)
            return False

    async def invalidate_group(self, group_name: str) -> None:
        """Delete all cached search results for a given group."""
        pattern = self._key(f"{group_name}:*")
        try:
            async with self.redis() as redis:
                cursor = 0
                while True:
                    cursor, keys = await redis.scan(cursor, match=pattern, count=200)
                    if keys:
                        await redis.delete(*keys)
                    if cursor == 0:
                        break
        except Exception as exc:
            logger.debug("search cache invalidate_group failed for '%s': %s", group_name, exc)

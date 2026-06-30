"""
Cache base classes for Criadex — mirrors Criabot's cache.core structure.

@author Kiarash Bashokian
"""

from __future__ import annotations

from abc import abstractmethod
from contextlib import asynccontextmanager
from typing import TypeVar

from pydantic import BaseModel
from redis import asyncio as aioredis
from redis.asyncio import ConnectionPool, Redis

T = TypeVar("T", bound=BaseModel)


class CacheObject:
    """Generic Redis cache object.

    Subclasses set ``key_prefix`` to namespace their keys and implement
    ``set / get / delete / exists``.
    """

    key_prefix: str = ""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    @asynccontextmanager
    async def redis(self):
        async with aioredis.Redis(connection_pool=self._pool) as redis:
            yield redis

    @abstractmethod
    async def set(self, key: str, val, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key: str, **kwargs) -> bool:
        raise NotImplementedError


class BaseCacheAPI:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    @property
    def pool(self) -> ConnectionPool:
        return self._pool

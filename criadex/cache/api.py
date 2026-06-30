"""
Top-level cache API for Criadex.

@author Kiarash Bashokian
"""

from redis.asyncio import ConnectionPool

from criadex.cache.core import BaseCacheAPI
from criadex.cache.objects.search_results import SearchResults


class CriadexCacheAPI(BaseCacheAPI):
    def __init__(self, pool: ConnectionPool) -> None:
        super().__init__(pool)
        self.search_results: SearchResults = SearchResults(pool)

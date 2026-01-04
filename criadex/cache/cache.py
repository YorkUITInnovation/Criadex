"""
Cache module for Criadex (Elasticsearch version)
Implements caching for database/API results, similar to Qdrant cache features.
"""

import time
from collections import OrderedDict
from criadex.core.event import Event

class Cache:
    """
    Cache for Criadex (Elasticsearch version)
    Supports LRU and TTL caching, and event-driven invalidation.
    """
    def __init__(self, mysql_api, max_size=128, ttl=300, event: Event = None):
        self.mysql_api = mysql_api
        self._cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.event = event or Event()

        # Listen for delete events to invalidate cache
        self.event.on(Event.DELETE, self.invalidate)

    def get(self, key):
        entry = self._cache.get(key)
        if entry:
            value, timestamp = entry
            if time.time() - timestamp < self.ttl:
                # Move to end (LRU)
                self._cache.move_to_end(key)
                return value
            else:
                # Expired
                self._cache.pop(key)
        return None

    def set(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (value, time.time())
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def clear(self):
        self._cache.clear()

    def invalidate(self, doc_id=None, **kwargs):
        # Invalidate cache for a specific doc_id or all
        if doc_id and doc_id in self._cache:
            self._cache.pop(doc_id, None)
        elif doc_id is None:
            self.clear()

    # Add more cache features as needed (custom invalidation, stats, etc.)

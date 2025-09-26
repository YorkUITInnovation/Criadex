"""
This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     kiarash b
@copyright  2025 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
"""


import asyncio
from typing import List, Dict, Any, Optional

class RagflowIndexRetriever:
    def __init__(self, vector_store, embedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def multi_collection_search(self, collections: List[str], query: str, top_k=10, query_filter: Optional[Dict[str, Any]] = None):
        query_embedding = self.embedder.embed(query)
        results = {}
        for collection in collections:
            hits = self.vector_store.search(collection, query_embedding, top_k=top_k, query_filter=query_filter)
            results[collection] = hits
        return results

    async def amulti_collection_search(self, collections: List[str], query: str, top_k=10, query_filter: Optional[Dict[str, Any]] = None):
        query_embedding = await self.embedder.aembed(query)
        results = {}
        for collection in collections:
            hits = await self.vector_store.asearch(collection, query_embedding, top_k=top_k, query_filter=query_filter)
            results[collection] = hits
        return results

    def add_metadata_to_results(self, results: Dict[str, Any], file_name=None, created_at=None, group_id=None):
        # Add metadata to all results
        for collection, hits in results.items():
            for doc in hits:
                if file_name:
                    doc["file_name"] = file_name
                if created_at:
                    doc["created_at"] = created_at
                if group_id:
                    doc["group_id"] = group_id
        return results

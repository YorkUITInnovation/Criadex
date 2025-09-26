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

from elasticsearch import Elasticsearch


from typing import Any, Dict, List, Optional, Union
import asyncio

class RagflowVectorStore:
    def __init__(self, host, port, username=None, password=None, index_name="criadex", group_name=None):
        self.es = Elasticsearch(
            hosts=[{"host": host, "port": port, "scheme": "http"}],
            basic_auth=(username, password) if username and password else None,
            verify_certs=False
        )
        self.index_name = index_name
        self.group_name = group_name

    def collection_exists(self, collection_name):
        return self.es.indices.exists(index=collection_name)

    async def acollection_exists(self, collection_name):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.collection_exists, collection_name)

    def create_collection(self, collection_name):
        if not self.es.indices.exists(index=collection_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "metadata": {
                            "properties": {
                                "file_name": {"type": "keyword"}
                            }
                        }
                    }
                }
            }
            self.es.indices.create(index=collection_name, body=mapping)

    async def acreate_collection(self, collection_name):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.create_collection, collection_name)

    def insert(self, collection_name, doc_id, embedding, text, metadata=None):
        import logging
        body = {"embedding": embedding, "text": text, "metadata": metadata or {}}
        if self.group_name:
            body["group_name"] = self.group_name
        print(f"--- DEBUG: ES INSERT: doc_id={doc_id}, text={text!r}, metadata={body.get('metadata')!r} ---")
        logging.info(f"Elasticsearch insert: doc_id={doc_id}, metadata={body.get('metadata')}")
        self.es.index(index=collection_name, id=doc_id, body=body, refresh=True)

    async def ainsert(self, collection_name, doc_id, embedding, text, metadata=None):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.insert, collection_name, doc_id, embedding, text, metadata)

    def delete(self, collection_name, doc_id):
        self.es.delete(index=collection_name, id=doc_id)

    async def adelete(self, collection_name, doc_id):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.delete, collection_name, doc_id)

    def delete_by_query(self, collection_name, field, value):
        query = {
            "query": {
                "term": {
                    f"metadata.{field}.keyword": value
                }
            }
        }
        self.es.delete_by_query(index=collection_name, body=query, refresh=True)

    async def adelete_by_query(self, collection_name, field, value):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.delete_by_query, collection_name, field, value)

    def merge_filters(self, *filters: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Merge multiple Elasticsearch filters (bool queries)
        must = []
        must_not = []
        should = []
        for f in filters:
            if not f:
                continue
            must.extend(f.get("must", []))
            must_not.extend(f.get("must_not", []))
            should.extend(f.get("should", []))
        merged = {"bool": {}}
        if must:
            merged["bool"]["must"] = must
        if must_not:
            merged["bool"]["must_not"] = must_not
        if should:
            merged["bool"]["should"] = should
        return merged

    def build_query_filter(self, query: Union[Dict[str, Any], None], extra_filter: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        # Merge base query filter and extra filter
        if query is None and extra_filter is None:
            return None
        if query is None:
            return extra_filter
        if extra_filter is None:
            return query
        return self.merge_filters(query, extra_filter)

    def search(self, collection_name, query_embedding, top_k=10, query_filter=None, sort=None):
        # Support for custom filters and group filtering
        base_query = {
            "bool": {
                "must": [
                    {
                        "script_score": {
                            "query": {"match_all": {}},
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                "params": {"query_vector": query_embedding}
                            }
                        }
                    }
                ]
            }
        }

        filters_to_apply = []
        if self.group_name:
            filters_to_apply.append({"term": {"group_name": self.group_name}})
        
        if query_filter:
            filters_to_apply.append(query_filter) # Append the query_filter directly

        if filters_to_apply:
            base_query["bool"]["filter"] = filters_to_apply

        # Always sort by updated_at descending to get the latest node first
        search_kwargs = {
            "index": collection_name,
            "query": base_query,
            "size": top_k,
            "sort": [{"metadata.updated_at": {"order": "desc"}}]
        }
        result = self.es.search(**search_kwargs)
        return result["hits"]["hits"]

    async def asearch(self, collection_name, query_embedding, top_k=10, query_filter=None, sort=None):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.search, collection_name, query_embedding, top_k, query_filter, sort)

    def add_metadata(self, doc: dict, file_name=None, created_at=None, group_id=None):
        # Add file/group metadata
        if file_name:
            doc["file_name"] = file_name
        if created_at:
            doc["created_at"] = created_at
        if self.group_name:
            doc["group_name"] = self.group_name
        if group_id:
            doc["group_id"] = group_id
        return doc

"""
This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     kiarash bashokian
@copyright  2025 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
"""

from elasticsearch import Elasticsearch, NotFoundError as ESNotFoundError
from criadex.schemas import IndexNotFoundError


from typing import Any, Dict, List, Optional, Union
import asyncio
import json
import hashlib
import re

class RagflowVectorStore:
    def __init__(self, host, port, username=None, password=None, index_name="criadex", group_name=None, embedding_dims=768):
        self.es = Elasticsearch(
            hosts=[{"host": host, "port": port, "scheme": "http"}],
            basic_auth=(username, password) if username and password else None,
            verify_certs=False,
            request_timeout=60,
            max_retries=3,
            retry_on_timeout=True
        )
        self.index_name = index_name
        self.group_name = group_name
        self.embedding_dims = embedding_dims

    def _to_es_index_name(self, collection_name: str) -> str:
        """Convert logical group names into Elasticsearch-safe index names."""
        base = re.sub(r"[^a-z0-9._-]+", "-", (collection_name or "").lower()).strip("-_.")
        if not base:
            base = "group"
        digest = hashlib.sha1((collection_name or "group").encode("utf-8")).hexdigest()[:8]
        # Keep names deterministic and under Elasticsearch index length limits.
        safe = f"{base}-{digest}"[:255]
        return safe

    def collection_exists(self, collection_name):
        return self.es.indices.exists(index=self._to_es_index_name(collection_name))

    async def acollection_exists(self, collection_name):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.collection_exists, collection_name)

    def create_collection(self, collection_name, embedding_dims=None):
        import logging
        index_name = self._to_es_index_name(collection_name)
        
        # Check if index already exists
        if self.es.indices.exists(index=index_name):
            # Verify it has the dense_vector embedding field
            try:
                mappings = self.es.indices.get_mapping(index=index_name)
                props = mappings[index_name].get('mappings', {}).get('properties', {})
                embedding_field = props.get('embedding', {})
                
                # If embedding field doesn't have dense_vector type, we have a schema mismatch
                if embedding_field.get('type') != 'dense_vector':
                    logging.error(
                        f"Index '{index_name}' exists but embedding field has wrong type: "
                        f"{embedding_field.get('type')}. Expected 'dense_vector'. "
                        f"Vector searches will fail. Delete the index and re-upload content."
                    )
            except Exception as e:
                logging.warning(f"Could not verify index schema for '{index_name}': {e}")
            return
        
        # Create the index with proper dense_vector mapping
        try:
            resolved_dims = int(embedding_dims or self.embedding_dims or 768)
            mapping = {
                "mappings": {
                    "properties": {
                        "metadata": {
                            "properties": {
                                "group_name": {"type": "keyword"},
                                "group_id": {"type": "keyword"},
                                "file_name": {"type": "keyword"},
                                "updated_at": {"type": "date"},
                                "update_id": {"type": "keyword"}
                            }
                        },
                        "embedding": {
                            "type": "dense_vector",
                            "dims": resolved_dims
                        },
                        "text": {"type": "text"},
                        "collection_name": {"type": "keyword"}
                    }
                }
            }
            self.es.indices.create(index=index_name, body=mapping)
            logging.info(f"Created Elasticsearch index '{index_name}' with {resolved_dims}-dim dense_vector embedding")
        except Exception as e:
            logging.error(
                f"Failed to create Elasticsearch index '{index_name}' with proper dense_vector mapping: {e}. "
                f"Subsequent vector searches will fail. "
                f"Ensure Elasticsearch is running and 'dense_vector' type is supported."
            )
            raise

    async def acreate_collection(self, collection_name, embedding_dims=None):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.create_collection, collection_name, embedding_dims)

    def insert(self, collection_name, doc_id, embedding, text, metadata=None):
        import logging
        index_name = self._to_es_index_name(collection_name)
        
        # Verify index exists and has proper schema BEFORE inserting
        if not self.es.indices.exists(index=index_name):
            raise IndexNotFoundError(
                f"Elasticsearch index '{index_name}' does not exist. "
                f"Call create_collection() first to ensure the index is created with proper dense_vector mapping. "
                f"Inserting without the index will cause Elasticsearch to auto-create it with wrong schema."
            )
        
        body = {"text": text, "embedding": embedding}
        if metadata:
            body["metadata"] = metadata
        body["collection_name"] = collection_name

        try:
            self.es.index(index=index_name, id=doc_id, document=body, refresh=True)
        except Exception as e:
            logging.error(f"Failed to insert document '{doc_id}' into index '{index_name}': {e}")
            raise

    async def ainsert(self, collection_name, doc_id, embedding, text, metadata=None):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.insert, collection_name, doc_id, embedding, text, metadata)

    def delete(self, collection_name, doc_id):
        self.es.delete(index=self._to_es_index_name(collection_name), id=doc_id)

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
        response = self.es.delete_by_query(index=self._to_es_index_name(collection_name), body=query, refresh=True)
        self.es.indices.refresh(index=self._to_es_index_name(collection_name))

    async def adelete_by_query(self, collection_name, field, value):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.delete_by_query, collection_name, field, value)

    def merge_filters(self, *filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Merge multiple Elasticsearch filters (bool queries)
        final_clauses = []
        for f in filters:
            if not f:
                continue
            if "bool" in f:
                if "must" in f["bool"]:
                    final_clauses.extend(f["bool"]["must"])
                if "should" in f["bool"]:
                    final_clauses.extend(f["bool"]["should"])
                if "must_not" in f["bool"]:
                    final_clauses.extend(f["bool"]["must_not"])
            elif "must" in f:
                final_clauses.extend(f["must"])
            elif "should" in f:
                final_clauses.extend(f["should"])
            elif "must_not" in f:
                final_clauses.extend(f["must_not"])
            else:
                final_clauses.append(f)
        return final_clauses

    def build_query_filter(self, query: Union[Dict[str, Any], None], extra_filter: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        # Merge base query filter and extra filter
        if query is None and extra_filter is None:
            return None
        if query is None:
            return extra_filter
        if extra_filter is None:
            return query
        return self.merge_filters(query, extra_filter)

    def _normalize_metadata_filter(self, query_filter: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize app-level filters into proper Elasticsearch bool query clauses.

        Supports:
        - {"must": {k: v, ...}, "should": [{k: v}, ...]}
        - {"bool": {...}} (passed through)
        """
        if not query_filter:
            return {"bool": {"filter": [{"match_all": {}}]}}

        if "bool" in query_filter:
            return query_filter

        must = query_filter.get("must") or {}
        should = query_filter.get("should") or []

        must_clauses: list[dict] = []
        for key, value in must.items():
            must_clauses.append({"term": {f"metadata.{key}": value}})

        should_clauses: list[dict] = []
        if isinstance(should, list):
            for cond in should:
                if not isinstance(cond, dict) or not cond:
                    continue
                k, v = next(iter(cond.items()))
                should_clauses.append({"term": {f"metadata.{k}": v}})

        bool_query: dict = {"filter": must_clauses or [{"match_all": {}}]}
        if should_clauses:
            bool_query["should"] = should_clauses
            bool_query["minimum_should_match"] = 1

        return {"bool": bool_query}

    def search(self, collection_name, query_embedding, top_k=10, query_filter=None, sort=None):
        normalized = self._normalize_metadata_filter(query_filter or {})

        # Construct the main query using function_score.
        # NOTE: bool.filter is AND; group OR semantics are handled via bool.should + minimum_should_match.
        main_query = {
            "function_score": {
                "query": {
                    "bool": normalized["bool"]
                },
                "functions": [
                    {
                        "script_score": {
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                "params": {"query_vector": query_embedding}
                            }
                        }
                    }
                ],
                "boost_mode": "multiply"
            }
        }
        

        search_kwargs = {
            "index": self._to_es_index_name(collection_name),
            "query": main_query,
            "size": top_k,
            "sort": [
                {"_score": {"order": "desc"}},
                {"metadata.updated_at": {"order": "desc"}},
            ],
            "track_scores": True
        }
        
        try:
            result = self.es.search(**search_kwargs)
        except ESNotFoundError as exc:
            raise IndexNotFoundError(
                f"Elasticsearch index for group '{collection_name}' not found. "
                "The group's content index may have been lost. Re-upload content to rebuild the index."
            ) from exc
        return result["hits"]['hits']

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
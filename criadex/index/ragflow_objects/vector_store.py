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
import json

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
                                "file_name": {"type": "keyword"},
                                "updated_at": {"type": "date"},
                                "update_id": {"type": "keyword"} # Add this line
                            }
                        },
                        "embedding": {
                            "type": "dense_vector",
                            "dims": 768
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
        body = {"text": text, "embedding": embedding}
        if metadata:
            body["metadata"] = metadata
        body["collection_name"] = collection_name # Add collection_name to the document
        logging.info(f"Elasticsearch insert: doc_id={doc_id}, metadata={body.get('metadata')}")
        
        self.es.index(index=collection_name, id=doc_id, document=body, refresh=True)

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
        response = self.es.delete_by_query(index=collection_name, body=query, refresh=True)
        self.es.indices.refresh(index=collection_name)

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

    def search(self, collection_name, query_embedding, top_k=10, query_filter=None, sort=None):
        # Build the filter clauses
        filters_to_merge = []

        # Add user-provided query filter
        if query_filter:
            filters_to_merge.append(query_filter)

        merged_filter_clauses = self.merge_filters(*filters_to_merge)
        
        # Construct the main query using function_score
        main_query = {
            "function_score": {
                "query": {
                    "bool": {
                        "filter": merged_filter_clauses if merged_filter_clauses else [{"match_all": {}}]
                    }
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
        

        # Always sort by updated_at descending to get the latest node first
        search_kwargs = {
            "index": collection_name, # Use collection_name as the index
            "query": main_query,
            "size": top_k,
            "sort": [{"metadata.updated_at": {"order": "desc"}}]
        }
        
        result = self.es.search(**search_kwargs)
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
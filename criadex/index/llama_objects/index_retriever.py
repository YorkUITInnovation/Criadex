"""

This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     Isaac Kogan
@copyright  2024 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later

"""

import dataclasses
from dataclasses import dataclass
from typing import Optional, Any, List, cast

from llama_index.core import QueryBundle
from llama_index.core.indices.vector_store import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore
from llama_index.core.vector_stores import VectorStoreQuery


@dataclass
class FilteredVectorStoreQuery(VectorStoreQuery):
    """
    A vector store query with a filter

    """

    query_filter: Optional[Any] = None


class FilteredQueryStr(str):
    """
    The query with a filter string

    """

    def __new__(cls, query_str: str, query_filter: Optional[Any]):
        instance = super(FilteredQueryStr, cls).__new__(cls, query_str)
        instance.query_filter = query_filter
        return instance

    def __init__(self, _, query_filter):
        self.query_filter = query_filter


class QdrantVectorIndexRetriever(VectorIndexRetriever):
    """
    Qdrant retriever that supports filtering & async search on top of the base retriever

    """

    async def afilter_retrieve(self, query_bundle: QueryBundle, query_filter: Optional[Any]) -> List[NodeWithScore]:
        """
        Retrieve from the database asynchronously with a filter

        :param query_bundle: The query bundle
        :param query_filter: The filter to add
        :return: The nodes with scores

        """

        # A special string gets created with the query filter as a property on it
        # This can then be accessed later on without dealing with LlamaIndex's horrible code nesting
        query_bundle.query_str = FilteredQueryStr(
            query_bundle.query_str,
            query_filter=query_filter
        )

        return await self._aretrieve(query_bundle)

    def _build_vector_store_query(
            self, query_bundle_with_embeddings: QueryBundle
    ) -> FilteredVectorStoreQuery:
        """
        Query bundle gets repackaged, we need to make sure our attribute is passed with it

        :param query_bundle_with_embeddings: The modded query bundle
        :return: The modded vector store query

        """

        query_filter = cast(FilteredQueryStr, query_bundle_with_embeddings.query_str).query_filter
        query_bundle_with_embeddings.query_str = str(query_bundle_with_embeddings.query_str)
        query: VectorStoreQuery = super()._build_vector_store_query(query_bundle_with_embeddings)

        return FilteredVectorStoreQuery(
            query_filter=query_filter,
            **(dataclasses.asdict(query))
        )

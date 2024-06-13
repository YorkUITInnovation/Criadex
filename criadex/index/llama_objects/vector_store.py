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

import logging
from typing import Optional, Any, Union, List

from llama_index.core.vector_stores import VectorStoreQuery
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import grpc as qgrpc, QdrantClient
from qdrant_client.http import models as qhttp

from criadex.index.llama_objects.index_retriever import FilteredVectorStoreQuery


class CriadexQdrantVectorStore(QdrantVectorStore):
    """
    Custom llama-index vector store for Qdrant that utilizes multitenancy with Criadex's "Group" System

    """

    def _build_query_filter(self, query: VectorStoreQuery) -> Optional[qhttp.Filter]:
        """
        We used a little trick in QdrantVectorIndexRetriever to repackage it with an optional filter.
        Now is the time to SHINE! We simply merge.

        :param query: The query
        :return: The Filter
        """

        # Allow the default to compile
        base_filter: Optional[Any] = super()._build_query_filter(query)

        # Check if we successfully passed our modified query object
        if not isinstance(query, FilteredVectorStoreQuery):
            logging.error("Received query missing filter. Likely LlamaIndex change, filtering will not work.")
            return base_filter

        # Check if the lib actually returned a working filter
        if not isinstance(base_filter, qhttp.Filter):
            logging.error("Received non-filter response. Likely LlamaIndex change, filtering will not work.")
            return base_filter

        query_filter: Optional[qhttp.Filter] = query.query_filter

        # Check if the user actually included any filter
        if query_filter is None:
            return base_filter

        # Check if they didn't include the right type
        if not isinstance(query_filter, qhttp.Filter):
            raise ValueError("Received the wrong type of filter object.")

        return merge_filters(base_filter, query_filter)

    def _create_collection(self, collection_name: str, vector_size: int, rest=None) -> None:
        """
        Create a collection with a vector size and rest of the parameters.
        Overrides default qdrant behaviour for custom Cria related groups.

        :param collection_name: The name of the collection
        :param vector_size: The size of the vector
        :param rest: The rest of the parameters
        :return: None

        """

        self._client: QdrantClient

        self._client.grpc_collections.Create(
            qgrpc.CreateCollection(
                collection_name=collection_name,
                vectors_config=qgrpc.VectorsConfig(
                    params=qgrpc.VectorParams(
                        size=vector_size,
                        distance=qgrpc.Distance.Value("Cosine")
                    ),

                ),

                # M=0 disables global index, VERY important
                # https://github.com/qdrant/qdrant/blob/master/docs/grpc/docs.md#qdrant-HnswConfigDiff
                hnsw_config=qgrpc.HnswConfigDiff(
                    m=0,
                    payload_m=16
                )
            )
        )

        # NEED to add group_name as its own index for multinenancy
        # https://github.com/qdrant/qdrant/blob/master/docs/grpc/docs.md#qdrant-HnswConfigDiff
        self._client.grpc_points.CreateFieldIndex(
            qgrpc.CreateFieldIndexCollection(
                collection_name=collection_name,
                field_name="group_name",
                field_type=qgrpc.FieldType.Value("FieldTypeKeyword")
            )
        )

        self._collection_initialized = True


def merge_filters(*filters: Union[qhttp.Filter, qgrpc.Filter]) -> Union[qhttp.Filter, qgrpc.Filter]:
    """
    Merge multiple Qdrant filters into one.

    :param filters: The filters to merge
    :return: The merged filter objects

    """

    if len(filters) < 1:
        raise ValueError("Must have 1 or more filters")

    if len(set(type(f) for f in filters)) > 1:
        raise ValueError("All filters must be same type")

    must: list[Union[qhttp.Condition, qgrpc.Condition]] = []
    must_not: List[Union[qhttp.Condition, qgrpc.Condition]] = []
    should: List[Union[qhttp.Condition, qgrpc.Condition]] = []

    for qdrant_filter in filters:

        if not qdrant_filter:
            continue

        must.extend(qdrant_filter.must or [])
        must_not.extend(qdrant_filter.must_not or [])
        should.extend(qdrant_filter.should or [])

    return type(filters[0])(
        must=must,
        must_not=must_not,
        should=should
    )

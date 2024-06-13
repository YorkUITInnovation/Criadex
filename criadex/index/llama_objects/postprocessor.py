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

from abc import abstractmethod
from typing import List, Optional

from cohere.responses import Reranking
from llama_index.core import QueryBundle
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore
from pydantic import PrivateAttr

from criadex.index.llama_objects.models import CriaCohereRerank


class MissingRerankQueryBundle(RuntimeError):
    """
    Thrown when the CohereRerankPostprocessor is missing the query bundle in the extra info.

    """


class AsyncBaseNodePostprocessor(BaseNodePostprocessor):
    """
    Base class for all node postprocessors that need to be asynchronous.

    """

    async def postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
            query_str: Optional[str] = None,
    ) -> List[NodeWithScore]:
        """
        Postprocess the nodes.

        :param nodes: The nodes to postprocess
        :param query_bundle: The query bundle
        :param query_str: The query string
        :return: The postprocessed nodes

        """

        if query_str is not None and query_bundle is not None:
            raise ValueError("Cannot specify both query_str and query_bundle")
        elif query_str is not None:
            query_bundle = QueryBundle(query_str)
        else:
            pass
        return await self._postprocess_nodes(nodes, query_bundle)

    @abstractmethod
    async def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """
        Postprocess the nodes.

        :param nodes: The nodes to postprocess
        :param query_bundle: The query bundle
        :return: The postprocessed nodes

        """

        raise NotImplementedError


class CohereRerankPostprocessor(AsyncBaseNodePostprocessor):
    """
    Override the base postprocessor to add Cohere reranking.

    """

    top_n: Optional[int] = None
    _reranker: CriaCohereRerank = PrivateAttr()

    def __init__(
            self,
            reranker: CriaCohereRerank,
            top_n: int
    ):
        """
        Initialize the CohereRerankPostprocessor.

        :param reranker: The Cohere reranker
        :param top_n: The top N nodes to return

        """

        self._reranker = reranker
        super().__init__(top_n=top_n)

    @classmethod
    def class_name(cls) -> str:
        """
        The class name.

        :return: Class name

        """

        return "CohereRerank"

    async def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """
        Rerank the nodes using the Cohere model.

        :param nodes: The nodes to rerank
        :param query_bundle: The query bundle
        :return: The reranked nodes

        """

        if query_bundle is None:
            raise MissingRerankQueryBundle("Missing query bundle in extra info.")

        if len(nodes) == 0:
            return []

        results: Reranking = await self._reranker.rerank(
            query=query_bundle,
            nodes=nodes,
            top_n=self.top_n or len(nodes)
        )

        new_nodes = []
        for result in results:
            # Fetch the node
            node: NodeWithScore = nodes[result.index]
            rerank_score: int = result.relevance_score

            # Update metadata
            node.node.metadata['vector_score'] = nodes[result.index].score
            node.node.metadata['rerank_score'] = rerank_score

            # Update the node
            new_node_with_score = NodeWithScore(
                node=node.node,
                score=rerank_score
            )

            new_nodes.append(new_node_with_score)

        new_nodes = sorted(nodes, key=lambda n: n.score)
        new_nodes.reverse()
        return new_nodes

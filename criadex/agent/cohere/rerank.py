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

import os
import sys
from typing import List, Optional, Any

from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle
from pydantic import BaseModel, Field

from criadex.criadex import Criadex
from criadex.index.index_api.document.index import DocumentIndexAPI
from criadex.index.index_api.document.index_objects import DocumentCohereRerank, MetadataKeys
from ...index.index_api.question.index_objects import QUESTION_NODE_ANSWER_KEY
from criadex.index.llama_objects.models import CriaCohereRerank
from ..base_agent import BaseAgent, BaseAgentResponse
from ...database.tables.models.cohere import CohereModelsModel
from ...index.base_api import CriadexIndexAPI
from ...index.schemas import MetaTextNode, TextNodeWithScore, ServiceConfig
from ...schemas import ModelNotFoundError


class PartialTextNodeWithScore(NodeWithScore):
    """
    Partial text node with score (used to fix weird llama-index inheritance bug)

    """

    node: MetaTextNode


class RerankAgentResponse(BaseAgentResponse):
    """
    Rerank agent response

    """

    ranked_nodes: List[TextNodeWithScore]
    search_units: int


class RerankAgentConfig(BaseModel):
    """
    Rerank agent configuration

    """

    prompt: str
    nodes: List[PartialTextNodeWithScore]

    # Rerank config
    top_n: Optional[int] = Field(default=None, ge=1)
    min_n: float = Field(default=0.0, ge=0.0, le=1.0)


class RerankAgent(BaseAgent):
    """
    Agent using the Cohere reranker to rerank nodes

    """

    def __init__(
            self,
            criadex: Criadex,
            cohere_model_id: int
    ):
        super().__init__()
        self._criadex: Criadex = criadex
        self._cohere_model_id: int = cohere_model_id
        self._node_postprocessors: Optional[List[BaseNodePostprocessor]] = None
        self._rerank_model: Optional[CriaCohereRerank] = None

    async def build_rerank_model(self):
        """
        Build the re-rank model

        :return: The re-rank model

        """

        if not self._rerank_model:

            model: Optional[CohereModelsModel] = await self._criadex.mysql_api.cohere_models.retrieve(
                model_id=self._cohere_model_id
            )

            if model is None:
                raise ModelNotFoundError("Model does not exist!")

            self._rerank_model = DocumentIndexAPI.build_rerank_model(
                rerank_model=model
            )

        return self._rerank_model

    async def build_node_postprocessors(self, config: RerankAgentConfig) -> List[BaseNodePostprocessor]:
        """
        Build the node postprocessors for re-ranking

        :return: The node postprocessor

        """

        if self._node_postprocessors is not None:
            return self._node_postprocessors

        await self.build_rerank_model()

        service_config: ServiceConfig = ServiceConfig(
            rerank_model=self._rerank_model
        )

        if not isinstance(service_config.rerank_model, CriaCohereRerank):
            raise ValueError("Must be a CriaCohereRerank model!")

        cohere_rerank: DocumentCohereRerank = DocumentCohereRerank(
            top_n=config.top_n or 10,
            reranker=service_config.rerank_model
        )

        self._node_postprocessors = [

            # Replace docs with their windows
            MetadataReplacementPostProcessor(
                target_metadata_key=MetadataKeys.WINDOW
            ),

            # Replace questions with their answer
            MetadataReplacementPostProcessor(
                target_metadata_key=QUESTION_NODE_ANSWER_KEY
            ),

            # Then add the re-ranker
            cohere_rerank

        ]

        return self._node_postprocessors

    async def execute(
            self,
            config: RerankAgentConfig
    ) -> RerankAgentResponse:
        """
        Rerank the nodes based on the prompt

        :param config: The rerank config
        :return: The reranked nodes as in a response object

        """

        await self.build_node_postprocessors(config)

        nodes = await CriadexIndexAPI.postprocess_nodes(
            query_bundle=QueryBundle(config.prompt),
            nodes=config.nodes,
            node_postprocessors=self._node_postprocessors
        )

        # Top N
        nodes = nodes[:config.top_n]

        # Min N
        nodes = [node for node in nodes if node.score >= config.min_n]

        # Return new nodes
        return RerankAgentResponse(
            ranked_nodes=nodes,
            search_units=1,
            message="Successfully re-ranked the nodes!"
        )

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

from typing import List, Optional

from criadex.index.ragflow_objects.postprocessor import RagflowMetadataReplacementPostProcessor
from criadex.index.ragflow_objects.postprocessor import RagflowBaseNodePostprocessor
from criadex.index.ragflow_objects.schemas import RagflowNodeWithScore, RagflowTextNode, RagflowQueryBundle
from pydantic import BaseModel, Field

from criadex.criadex import Criadex
from criadex.index.index_api.document.index import DocumentIndexAPI
from criadex.index.index_api.document.index_objects import DocumentCohereRerank, MetadataKeys
from criadex.index.ragflow_objects.models import RagflowReranker
from criadex.index.ragflow_objects.rerank import RagflowRerankAgent, RagflowRerankAgentResponse
from ...database.tables.models.cohere import CohereModelsModel
from ...index.base_api import CriadexIndexAPI
from ...index.index_api.question.index_objects import QUESTION_NODE_ANSWER_KEY
from ...index.schemas import ServiceConfig
from ...schemas import ModelNotFoundError


class CriaTextNode(RagflowTextNode):
    pass


class TextNodeWithScore(RagflowNodeWithScore):
    pass


class RerankAgentResponse(RagflowRerankAgentResponse):
    pass


class RerankAgentConfig(BaseModel):
    """
    Rerank agent configuration

    """

    prompt: str
    nodes: List[TextNodeWithScore]

    # Rerank config
    top_n: Optional[int] = Field(default=None, ge=1)
    min_n: float = Field(default=0.0, ge=0.0, le=1.0)


class RerankAgent(RagflowRerankAgent):
    """
    Ragflow-based RerankAgent with legacy feature parity: node postprocessing, top N/min N filtering, error handling.
    """

    async def execute(self, config: RerankAgentConfig) -> RerankAgentResponse:
        """
        Rerank the nodes based on the prompt, preserving legacy features.
        :param config: The rerank config
        :return: RerankAgentResponse
        """
        # Build node postprocessors (Ragflow API assumed)
        postprocessors = [
            RagflowMetadataReplacementPostProcessor(target_metadata_key="window"),
            RagflowMetadataReplacementPostProcessor(target_metadata_key="answer"),
            RagflowReranker(top_n=config.top_n or 10)
        ]
        # Postprocess nodes (Ragflow API assumed)
        nodes = await self.postprocess_nodes(
            query_bundle=RagflowQueryBundle(config.prompt),
            nodes=config.nodes,
            node_postprocessors=postprocessors
        )
        # Top N
        nodes = nodes[:config.top_n] if config.top_n else nodes
        # Min N
        nodes = [node for node in nodes if node.score >= config.min_n]
        return RerankAgentResponse(
            ranked_nodes=[TextNodeWithScore(node=node.node, score=node.score) for node in nodes],
            search_units=1,
            message="Successfully re-ranked the nodes!"
        )

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

import json
from typing import List, Sequence, Any, Optional

from llama_index.core.node_parser import NodeParser
from llama_index.core.node_parser.node_utils import build_nodes_from_splits
from llama_index.core.schema import BaseNode, NodeWithScore, QueryBundle, Document, TextNode
from pydantic import BaseModel, Field

from ...llama_objects.postprocessor import CohereRerankPostprocessor
from ...llama_objects.schemas import CriadexFile


class RelatedPrompt(BaseModel):
    label: str
    prompt: str
    llm_generated: bool = False


class QuestionConfig(BaseModel):
    """
    JSON file model for inserting into the question index

    """

    questions: List[str]
    answer: str
    llm_reply: bool = True
    related_prompts: List[RelatedPrompt] = Field(default_factory=list)


class QuestionParser(NodeParser):
    """
    Node parser for the Question index

    """

    @classmethod
    def class_name(cls) -> str:
        """
        Llama-index class name definition

        :return: The class name

        """

        return "question_parser"

    def get_nodes_from_documents(
            self,
            documents: Sequence[Document],
            show_progress: bool = False,
            **kwargs
    ) -> List[BaseNode]:
        """
        Convert an array of documents into an array of nodes

        :param documents: List of documents
        :param show_progress: Not used
        :param kwargs: Llama-index options
        :return: List of generated nodes

        """

        all_nodes: List[BaseNode] = []

        for document in documents:
            new_nodes: List[TextNode] = build_nodes_from_splits(
                text_splits=self._get_text_splits(document),  # 1 Text-split = 1 TextNode
                document=document
            )

            for node in new_nodes:
                node.metadata = document.metadata

            all_nodes.extend(new_nodes)

        return all_nodes

    def _parse_nodes(self, nodes: Sequence[BaseNode], show_progress: bool = False, **kwargs: Any) -> List[BaseNode]:
        """
        Not needed by this subclass...

        :param nodes: N/A
        :param show_progress: N/A
        :param kwargs: N/A
        :return: N/A

        """

        raise NotImplementedError

    @classmethod
    def _get_text_splits(cls, document: Document) -> List[str]:
        """
        The document text is an ARRAY of ways the question was asked
        ["What day is it?", "The day is what again?"] ...and so on

        :param document: The document
        :return: List of splits by question

        """

        return QuestionConfig(**json.loads(document.text)).questions


class QuestionCohereRerank(CohereRerankPostprocessor):
    """
    Re-ranker for the Question index

    """

    @classmethod
    def dedupe_question_nodes(
            cls,
            nodes: List[NodeWithScore]
    ) -> List[NodeWithScore]:
        """
        Dedupe question nodes (multiple examples may have been retrieved)

        :param nodes: The nodes to dedupe
        :return: The deduped nodes

        """

        deduped_nodes: List[NodeWithScore] = []
        file_names: List[str] = []

        # First de-dupe results
        for node in nodes:
            try:
                file_name: str = node.metadata[CriadexFile.FILE_NAME_META_STR]
            except KeyError as ex:
                raise KeyError("File name not found in node metadata! Womp womp.") from ex

            if file_name not in file_names:
                file_names.append(file_name)
                deduped_nodes.append(node)

        return deduped_nodes

    async def postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
            **kwargs
    ) -> List[NodeWithScore]:
        """
        Take each node & re-rank it based on the Question-Answer pair and how THAT relates to the user's query

        :param nodes: The retrieved nodes
        :param query_bundle: The query
        :param kwargs: Llama-index options
        :return: The nodes, with rankings

        """

        # Remove dupes
        deduped_nodes: List[NodeWithScore] = self.dedupe_question_nodes(nodes)

        # Create the Q&A pair
        for idx, node in enumerate(nodes):
            answer = node.metadata.get(QUESTION_NODE_ANSWER_KEY)
            node.node.text = f"{node.text}\n{answer}"

        response_nodes: List[NodeWithScore] = await super().postprocess_nodes(deduped_nodes, query_bundle)

        # Return nodes
        return response_nodes


QUESTION_NODE_ANSWER_KEY: str = "answer"
QUESTION_NODE_LLM_REPLY: str = "llm_reply"  # Make sure if changing to update in Criabot
QUESTION_NODE_RELATED_PROMPTS: str = "related_prompts"

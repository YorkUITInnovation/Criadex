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

from criadex.index.ragflow_objects.document_parser import RagflowDocumentParser
from criadex.index.ragflow_objects.schemas import RagflowBaseNode, RagflowNodeWithScore, RagflowDocument, RagflowTextNode
from pydantic import BaseModel, Field

## Removed legacy llama_objects imports


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


class QuestionParser(RagflowDocumentParser):
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
        documents: Sequence[RagflowDocument],
        show_progress: bool = False,
        **kwargs
    ) -> List[RagflowBaseNode]:
        """
        Convert an array of documents into an array of nodes

        :param documents: List of documents
        :param show_progress: Not used
        :param kwargs: Llama-index options
        :return: List of generated nodes

        """

        all_nodes: List[RagflowBaseNode] = []
        for document in documents:
            text_splits = self._get_text_splits(document)
            new_nodes: List[RagflowTextNode] = [
                RagflowTextNode(
                    id_=f"{document.doc_id}_{i}",
                    text=split,
                    metadata=document.metadata
                ) for i, split in enumerate(text_splits)
            ]
            all_nodes.extend(new_nodes)
        
        seen_texts = set()
        deduped_nodes = []
        for node in all_nodes:
            if node.text not in seen_texts:
                seen_texts.add(node.text)
                deduped_nodes.append(node)

        return deduped_nodes

    def _parse_nodes(self, nodes: Sequence[RagflowBaseNode], show_progress: bool = False, **kwargs: Any) -> List[RagflowBaseNode]:
        """
        Not needed by this subclass...

        :param nodes: N/A
        :param show_progress: N/A
        :param kwargs: N/A
        :return: N/A

        """

        raise NotImplementedError

    @classmethod
    def _get_text_splits(cls, document: RagflowDocument) -> List[str]:
        """
        The document text is an ARRAY of ways the question was asked
        ["What day is it?", "The day is what again?"] ...and so on

        :param document: The document
        :return: List of splits by question

        """

        return QuestionConfig(**json.loads(document.text)).questions





QUESTION_NODE_ANSWER_KEY: str = "answer"
QUESTION_NODE_LLM_REPLY: str = "llm_reply"  # Make sure if changing to update in Criabot
QUESTION_NODE_RELATED_PROMPTS: str = "related_prompts"

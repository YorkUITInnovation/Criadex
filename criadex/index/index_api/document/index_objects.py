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
import enum
import json
import uuid
from dataclasses import dataclass
from typing import List, Sequence, Any, Optional, Union

from criadex.index.ragflow_objects.document_parser import RagflowDocumentParser, default_id_func
from criadex.index.ragflow_objects.postprocessor import RagflowNodePostprocessor
from criadex.index.ragflow_objects.schemas import RagflowBaseNode, RagflowTextNode, RagflowDocument, RagflowNodeRelationship, RagflowNodeWithScore
from pydantic import BaseModel, Field

## Removed legacy llama_objects import
from criadex.index.schemas import RawAsset


class ElementType(enum.Enum):
    """
    The type of element in the document

    """

    FIGURE_CAPTION = "FigureCaption"
    NARRATIVE_TEXT = "NarrativeText"
    LIST_ITEM = "ListItem"
    TITLE = "Title"
    ADDRESS = "Address"
    TABLE = "Table"
    PAGE_BREAK = "PageBreak"
    HEADER = "Header"
    FOOTER = "Footer"
    UNCATEGORIZED_TEXT = "UncategorizedText"
    IMAGE = "Image"
    FORMULA = "Formula"

    # Custom
    UNKNOWN = "Unknown"
    TABLE_ENTRY = "TableEntry"
    BACKWARDS_COMPATIBLE_ASSET_CONTAINER = "BackwardsCompatibleAssetContainer"


@dataclass()
class Element:
    """
    An instance of an element in a document

    """

    type: ElementType
    text: str
    metadata: dict = dataclasses.field(default_factory=dict)
    element_id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))


class MetadataKeys:
    """
    Metadata keys for the document index

    """

    ORIGINAL = "original_text"  # Just string
    WINDOW = "window"  # Tagged + Window
    TAGGED = "tagged"  # Just tagged
    DOC_ID = "doc_id"
    TABLE = "table"


class DocumentConfig(BaseModel):
    """
    JSON file model for inserting into the question index

    """

    assets: List[RawAsset] = Field(default_factory=list)
    nodes: List[Element]


## Remove legacy CohereRerankPostprocessor class


class FuzzyMetadataDuplicateRemovalPostProcessor(RagflowNodePostprocessor):
    """
    Remove duplicates

    """

    target_metadata_key: str = Field(
        description="Target metadata key to replace node content with."
    )

    def __init__(self, target_metadata_key: str) -> None:
        super().__init__(target_metadata_key=target_metadata_key)

    @classmethod
    def class_name(cls) -> str:
        return "MetadataReplacementPostProcessor"

    def postprocess_nodes(
            self,
            nodes: List[Union[RagflowTextNode, RagflowNodeWithScore]],
            _=None,
            __=None,
    ):
        return self._postprocess_nodes(nodes)

    def _postprocess_nodes(
            self,
            nodes: List[RagflowTextNode],
            _finished_reverse: bool = False
    ):
        deduped_nodes: List[RagflowTextNode] = []

        for node in nodes:
            for deduped_node in deduped_nodes:
                window_str: Optional[str] = node.metadata.get(self.target_metadata_key)
                if (window_str and deduped_node.text in window_str) and deduped_node.text not in node.text:
                    node.metadata[self.target_metadata_key] = window_str.replace(deduped_node.text, "")
            deduped_nodes.append(node)

        deduped_nodes.reverse()

        if not _finished_reverse:
            return self._postprocess_nodes(deduped_nodes, True)

        return deduped_nodes


class DocumentParser(RagflowDocumentParser):
    """
    Parser for the document index. Takes document nodes in the above format (based on unstructured-api) and outputs Llama-Index nodes

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
            new_nodes: List[RagflowBaseNode] = self.build_nodes_from_document(document=document)
            all_nodes.extend(new_nodes)
        return all_nodes

    @classmethod
    def build_nodes_from_document(cls, document: RagflowDocument) -> List[RagflowTextNode]:
        """
        Build nodes from the document

        :param document: The document to build nodes from
        :return: The generated nodes

        """

        config: DocumentConfig = DocumentConfig(**json.loads(document.text))
        nodes: List[RagflowTextNode] = []
        relationships = {RagflowNodeRelationship.SOURCE: document.as_related_node_info()}
        for i, raw_node in enumerate(config.nodes):
            new_node = RagflowTextNode(
                id_=default_id_func(i, document),
                text=raw_node.text,
                excluded_embed_metadata_keys=document.excluded_embed_metadata_keys,
                excluded_llm_metadata_keys=document.excluded_llm_metadata_keys,
                metadata_separator=document.metadata_separator,
                metadata_template=document.metadata_template,
                text_template=document.text_template,
                relationships=relationships,
                metadata={**document.metadata, **raw_node.metadata}
            )
            nodes.append(new_node)
        return nodes

    def _parse_nodes(self, nodes: Sequence[RagflowBaseNode], show_progress: bool = False, **kwargs: Any) -> List[RagflowBaseNode]:
        """
        Not needed by this subclass...

        :param nodes: N/A
        :param show_progress: N/A
        :param kwargs: N/A
        :return: N/A

        """

        raise NotImplementedError

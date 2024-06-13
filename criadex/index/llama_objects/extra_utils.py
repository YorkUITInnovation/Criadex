from typing import Sequence, Any

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.node_parser import NodeParser
from llama_index.core.schema import TextNode, BaseNode
from tiktoken import encoding_for_model, Encoding

from criadex.index.llama_objects.models import CriaAzureOpenAI

TOKEN_COUNT_METADATA_KEY: str = "token_count"


def add_token_count_to_text_nodes(
        nodes: Sequence[BaseNode],
        model_name: str
) -> Sequence[BaseNode]:
    """
    Add token count to text nodes

    :param nodes: Nodes to add token count to
    :param model_name: Model to use for tokenizing (e.g. "gpt-3.5-turbo")
    :return: None

    """

    encoding: Encoding = encoding_for_model(model_name)

    for node in nodes:
        if not isinstance(node, TextNode):
            continue

        token_count = CriaAzureOpenAI.string_tokens(
            node.text,
            encoding=encoding
        )

        node.metadata[TOKEN_COUNT_METADATA_KEY] = token_count

    return nodes


class NodeTokenParser(NodeParser):
    """
    Simple token parser that calculates the token count for each text node

    """

    embedding_model: BaseEmbedding

    @classmethod
    def class_name(cls) -> str:
        """
        The name of the class

        :return: Class name

        """

        return "NodeTokenParser"

    def _parse_nodes(
            self,
            nodes: Sequence[BaseNode],
            show_progress: bool = False,
            **kwargs: Any,
    ) -> Sequence[BaseNode]:
        """
        Parse the nodes, adding the token count to text nodes

        :param nodes: Nodes to parse
        :param show_progress: Whether to show progress (ignored)
        :param kwargs: Extra arguments
        :return: The parsed nodes

        """

        return add_token_count_to_text_nodes(
            nodes=nodes,
            model_name=self.embedding_model.model_name
        )

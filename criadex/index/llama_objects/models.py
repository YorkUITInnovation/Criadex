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

from __future__ import annotations

from typing import Any, Dict, List, Union, Optional

import tiktoken
from cohere import AsyncClient
from cohere.responses import Reranking
from llama_index.core import BasePromptTemplate, ChatPromptTemplate, QueryBundle
from llama_index.core.base.llms.types import CompletionResponse, ChatResponse, ChatMessage
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.llms.azure_openai import AzureOpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion
from pydantic import PrivateAttr
from tiktoken import Encoding

from criadex.index.llama_objects.schemas import Reranker


class CriaEmbedding(AzureOpenAIEmbedding):
    """
    Instance of the LlamaIndex Embedding model

    """


class EmptyPromptError(RuntimeError):
    """
    Thrown when an empty prompt is provided

    """


class ContentFilterError(Exception):
    """
    Thrown when the Azure content filter is hit

    """


class CriaCohereRerank(Reranker):
    """
    Instance of the LlamaIndex Cohere Rerank model

    """

    def __init__(
            self,
            client: AsyncClient,
            model: str
    ):
        """
        Instantiate the Cohere Rerank Model

        :param client: The Cohere client
        :param model: The model name

        """

        self._model: str = model
        self._client: AsyncClient = client

    async def rerank(
            self,
            query: Union[str, QueryBundle],
            nodes: List[NodeWithScore],
            top_n: Optional[int] = None,
            **kwargs
    ) -> Reranking:
        """
        Rerank the nodes using the Cohere model

        :param query: The query string to rerank with
        :param nodes: The nodes to rerank
        :param top_n: The top N nodes to return
        :param kwargs: Any additional arguments
        :return: Returns the reranked nodes

        """

        if isinstance(query, QueryBundle):
            query = query.query_str

        return await self._client.rerank(
            query=query,
            documents=[node.get_content() for node in nodes],
            top_n=top_n,
            model=kwargs.pop('model', self._model),
            **kwargs
        )


class CriaAzureOpenAI(AzureOpenAI):
    """
    Instance of the LlamaIndex LLM model

    """

    def _prepare_chat_with_tools(self, tools: List["BaseTool"], user_msg: Optional[Union[str, ChatMessage]] = None, chat_history: Optional[List[ChatMessage]] = None, verbose: bool = False, allow_parallel_tool_calls: bool = False,
                                 **kwargs: Any) -> Dict[str, Any]:
        pass

    _token_usages: Dict[int, List[CompletionUsage]] = PrivateAttr(default_factory=dict)

    def __init__(self, **kwargs: Any):
        """
        Instantiate the Azure OpenAI LLM Model

        :param credentials: Model credentials retrieved from DB
        :param kwargs: Optional additional arguments
        """

        super().__init__(
            **kwargs
        )

    @classmethod
    def validate_env(cls, _: Dict[str, Any]) -> str:
        """
        Disable guard rails requiring globals to be set that don't need to be.

        :param _: N/A
        :return: N/A

        """

        return "Nice try, Logan. I know better."

    @classmethod
    def _escape_prompt_str(cls, prompt_str: str) -> str:
        """
        Escape the prompt string

        :param prompt_str: The prompt string
        :return: The escaped prompt string

        """

        return prompt_str \
            .replace("{", "{{") \
            .replace("}", "}}")

    @classmethod
    def escape_chat_prompt_templates(cls, template: BasePromptTemplate) -> None:
        """
        Escape the chat prompt templates

        :param template: The chat prompt template
        :return: Escaped chat prompt template

        """

        # note to self: don't escape PromptTemplate because it's a real template lol, just ChatPromptTemplate

        if isinstance(template, ChatPromptTemplate):
            for idx, m_template in enumerate(template.message_templates):
                template.message_templates[idx].content = cls._escape_prompt_str(
                    m_template.content
                )

    def predict(
            self,
            prompt: BasePromptTemplate,
            return_as_str: bool = True,
            **prompt_args: Any,
    ) -> Union[str, CompletionResponse, ChatResponse]:
        """
        (sync) Run LLM prediction

        :param prompt: The prompt to run
        :param return_as_str: Whether to return as a string
        :param prompt_args: Extra arguments
        :return: The response

        """

        # Escape JSON in prompts
        self.escape_chat_prompt_templates(prompt)

        if self.metadata.is_chat_model:
            prompt: List[ChatMessage] = self._get_messages(prompt, **prompt_args)
            self.validate_prompt(prompt)
            response: ChatResponse = self.chat(prompt)
        else:
            prompt: str = self._get_prompt(prompt, **prompt_args)
            self.validate_prompt(prompt)
            response: CompletionResponse = self.complete(prompt)

        query: Union[QueryBundle, str] = prompt_args.get("query_bundle", prompt_args.get("query_str"))
        return self.log(response, query, prompt, return_as_str)

    async def apredict(
            self,
            prompt: BasePromptTemplate,
            return_as_str: bool = True,
            **prompt_args: Any,
    ) -> Union[str, CompletionResponse, ChatResponse]:
        """
        (async) Run LLM prediction

        :param prompt: The prompt to run
        :param return_as_str: Whether to return as a string
        :param prompt_args: Extra arguments
        :return: The response

        """

        # Escape JSON in prompts
        self.escape_chat_prompt_templates(prompt)

        if self.metadata.is_chat_model:
            prompt: List[ChatMessage] = self._get_messages(prompt, **prompt_args)
            self.validate_prompt(prompt)
            response: ChatResponse = await self.achat(prompt)
            query: str = self.get_prompt(prompt)
        else:
            prompt: str = self._get_prompt(prompt, **prompt_args)
            self.validate_prompt(prompt)
            response: CompletionResponse = await self.acomplete(prompt)
            query: Union[QueryBundle, str] = prompt_args.get("query_bundle", prompt_args.get("query_str"))

        return self.log(response, query, prompt, return_as_str)

    @classmethod
    def node_tokens(cls, *node: TextNode, encoding: Optional[Encoding] = None) -> int:
        """
        Returns the list of tokens for a TextNode

        :param encoding: The encoding to check
        :param node: The node(s) being analyzed
        :return: The # of tokens

        """

        all_text: str = " ".join([n.text for n in node])
        return cls.string_tokens(all_text, encoding=encoding)

    @classmethod
    def string_tokens(cls, string: str, encoding: Optional[Encoding] = None) -> int:
        """
        Returns the number of tokens in a text string.

        Based on https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
        "cl100k_base" works for models gpt-4, gpt-3.5-turbo, text-embedding-ada-002

        """

        encoding = encoding or tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(string))

        return num_tokens

    @classmethod
    def message_tokens(cls, message: ChatMessage, encoding: Optional[Encoding] = None) -> int:
        """
        Returns the number of tokens in a ChatMessage.

        Based on https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
        "cl100k_base" works for models gpt-4, gpt-3.5-turbo, text-embedding-ada-002

        """

        return cls.string_tokens(
            string=message.content,
            encoding=encoding
        )

    def pop_hash(self, prompt: str) -> List[CompletionUsage]:
        """
        Pop the token usage from the token usage list

        :param prompt: The prompt to pop
        :return: The token usage

        """

        return self._token_usages.pop(self.get_hash(prompt), list())

    @classmethod
    def get_prompt(cls, messages: List[ChatMessage]) -> str:
        """
        Get the prompt from a list of messages

        :param messages: The list of messages
        :return: The prompt

        """

        return messages[-1].content

    @classmethod
    def get_hash(cls, prompt: Union[str, List[ChatMessage]]) -> int:
        """
        Convert a prompt to a hash

        :param prompt: The prompt to hash
        :return: The hash

        """
        return hash(prompt)

    @classmethod
    def validate_prompt(cls, prompt: Union[str, List[ChatMessage]]) -> None:
        """
        Validate if a prompt is empty

        :param prompt: The prompt to check
        :return: None

        """

        if isinstance(prompt, list):
            if len(prompt) < 1:
                raise EmptyPromptError("Prompt of type 'List[ChatMessage]' and no prompt provided.")
            if isinstance(prompt[0], ChatMessage):
                prompt: str = cls.get_prompt(prompt)
        if isinstance(prompt, str) and len(prompt) < 1:
            raise EmptyPromptError("Prompt of type 'str' was empty and cannot be used.")

    def log(
            self,
            response: Union[CompletionResponse, ChatResponse],
            query: Union[QueryBundle, str],
            prompt: Union[List[ChatMessage], str],
            return_as_str: bool
    ) -> Union[str, CompletionResponse, ChatResponse]:
        """
        Log the token usage for the response

        :param response: The response
        :param query: The query
        :param prompt: The prompt
        :param return_as_str: Whether to return as a string
        :return: The response

        """

        # Extract query string
        query: str = query.query_str if isinstance(query, QueryBundle) else query or str()

        # Find the message content
        content: str = (response.message.content if isinstance(response, ChatResponse) else response.text) or str()

        # If we receive completion back
        if response.raw.usage:
            completion_usage: CompletionUsage = response.raw.usage

        # If we have to manually calculate it
        else:

            # Encoding
            encoding: Optional[Encoding] = tiktoken.encoding_for_model(model_name=self.model)

            # Prompt tokens
            prompt_tokens: int = (
                sum(self.message_tokens(m, encoding=encoding) for m in prompt)
                if isinstance(prompt[0], ChatMessage) else
                self.string_tokens(prompt)
            )

            # Completion tokens
            completion_tokens: int = self.string_tokens(string=content, encoding=encoding)

            # Build usage
            completion_usage: CompletionUsage = CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )

        query_hash: int = self.get_hash(query)

        # Log the token usage
        self._token_usages[query_hash] = [
            completion_usage,
            *(self._token_usages.get(query_hash, []))
        ]

        return content if return_as_str else response

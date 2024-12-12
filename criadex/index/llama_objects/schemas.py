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

import time
from abc import ABC, abstractmethod
from typing import Optional, ClassVar, List, Any, Union, Sequence

from llama_index.core import Document, QueryBundle
from llama_index.core.schema import NodeWithScore


class Reranker(ABC):
    """
    Reranker interface for Criadex

    """

    @abstractmethod
    async def rerank(
            self,
            query: Union[str, QueryBundle],
            nodes: List[NodeWithScore],
            top_n: Optional[int] = None,
            **kwargs
    ) -> Any:
        raise NotImplementedError


class EmptyCriadexFile(RuntimeError):
    """
    Exception for when an empty file is provided to CriadexFile

    """


class CriadexFile(Document):
    """
    A file that can be inserted into the index

    """

    FILE_NAME_META_STR: ClassVar[str] = "file_name"
    FILE_CREATED_AT_META_STR: ClassVar[str] = "created_at"
    FILE_GROUP_META_STR: ClassVar[str] = "group_name"
    FILE_GROUP_ID_META_STR: ClassVar[str] = "group_id"

    @classmethod
    def create(
            cls,
            file_name: str,
            file_group: str,
            file_group_id: int,
            file_metadata: dict,
            text: Optional[str] = None,
    ) -> Optional[CriadexFile]:
        """
        Create a CriadexFile object

        :param file_name: The name of the file
        :param file_group: The group name of the file
        :param file_group_id: The group id of the file
        :param file_metadata: The metadata for the file
        :param text: The text of the file
        :return: The CriadexFile object

        """

        if not text:
            raise EmptyCriadexFile("Empty file provided to CriadexFile!")

        metadata: dict = {
            **file_metadata,
            cls.FILE_GROUP_META_STR: file_group,
            cls.FILE_NAME_META_STR: file_name,
            cls.FILE_CREATED_AT_META_STR: round(time.time()),
            cls.FILE_GROUP_ID_META_STR: file_group_id
        }

        # Default behaviour is to exclude all keys
        excluded_llm_keys: List[str] = cls._exclude_keys(
            metadata
        )

        excluded_embed_keys: List[str] = [*excluded_llm_keys, 'image_base64']

        return cls(
            text=text,
            doc_id=file_name,
            metadata=metadata,
            excluded_llm_metadata_keys=excluded_llm_keys,
            excluded_embed_metadata_keys=excluded_embed_keys
        )

    @classmethod
    def _exclude_keys(cls, metadata: dict, *allowed_keys: str) -> List[str]:
        """
        The keys to exclude from being added into the node text

        :param metadata: The metadata object
        :param allowed_keys: The keys to allow
        :return: The keys to exclude

        """

        exclude_keys: List[str] = []

        for key in metadata.keys():
            if key in allowed_keys:
                continue
            exclude_keys.append(key)

        return exclude_keys

    def exclude_all(self) -> None:
        """
        Exclude all keys

        :return: None

        """

        self.exclude_keys(
            keys=list(self.metadata.keys())
        )

    def exclude_keys(self, keys: Sequence[str]) -> None:
        """
        The keys to exclude from being added into the node text

        :param keys: The keys to exclude
        :return: The keys to exclude

        """

        excluded_llm_metadata_keys = set(self.excluded_llm_metadata_keys)
        excluded_embed_metadata_keys = set(self.excluded_embed_metadata_keys)

        self.excluded_llm_metadata_keys = list(excluded_llm_metadata_keys.union(keys))
        self.excluded_embed_metadata_keys = list(excluded_embed_metadata_keys.union(keys))

    @property
    def group_name(self) -> str:
        """
        The group name associated with the file

        :return: The group name associated with the file

        """

        return self.metadata.get(self.FILE_GROUP_META_STR)

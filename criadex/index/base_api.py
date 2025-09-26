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
from typing import Optional, List, Sequence, Generic, Any, Dict

from typing import Optional, List, Generic, Any, Dict
from criadex.index.schemas import ServiceConfig, BundleConfig
from ..database.api import GroupDatabaseAPI
from ..database.tables.groups import GroupsModel
from criadex.index.ragflow_objects.schemas import RagflowDocument, RagflowQuery

from pydantic import BaseModel

class ContentUploadConfig(BaseModel):
    """
    Configuration for uploading content to the index
    """
    file_name: str
    file_contents: dict
    file_metadata: dict

class CriadexIndexAPI(Generic[BundleConfig]):
    def _matches_filter(self, node: dict, search_filter: Dict[str, Any]) -> bool:
        """
        Basic application-layer filter logic migrated from Qdrant/MySQL to Ragflow/Elasticsearch.
        Supports structure: {"must": {k: v, ...}, "should": [{k: v}, ...]}
        Keys are matched against node.metadata values.
        """
        if not search_filter:
            return True
        metadata = node.get('metadata', {}) or {}
        must = search_filter.get('must', {})
        for key, value in must.items():
            if metadata.get(key) != value:
                return False
        should = search_filter.get('should', [])
        if should:
            if not any(metadata.get(list(cond.keys())[0]) == list(cond.values())[0] for cond in should if cond):
                return False
        return True

    """
    API Wrapper for interacting with Ragflow/Elasticsearch-wrapped vector collections

    """

    TOP_N: int = None  # Let the CLIENT decide what is relevant. Pull & rank ALL
    MAX_TOP_K: int = 1000  # Limit the user to a max top K for resource usage purposes

    def __init__(
        self,
        service_config: ServiceConfig,
        postgres_api: GroupDatabaseAPI,
        elasticsearch_client: Any = None
    ):
        self._service_config: ServiceConfig = service_config
        self._index: Optional[Any] = None
        self._postgres_api: GroupDatabaseAPI = postgres_api
        self._elasticsearch_client = elasticsearch_client


    async def search(self, config: dict) -> dict:
        """
        Search the index group & receive relevant data
        :param config: Configuration for searching
        :return: The response
        """
        # Ragflow/Elasticsearch search logic should go here
        return {}


    async def _search(self, config: dict) -> list:
        """
        Search the index & receive relevant data as a string
        :param config: Configuration for searching the index
        :return: List of nodes, with their associated, re-ranked scores
        """
        # Ragflow/Elasticsearch search logic should go here
        return []


    @classmethod
    async def postprocess_nodes(
        cls,
        nodes: List[Any],
        node_postprocessors: List[Any],
        query: Optional[Any] = None
    ) -> List[Any]:
        """
        Apply various postprocessors to the nodes
        :param nodes: The nodes to postprocess
        :param node_postprocessors: The postprocessors to apply
        :param query: Optional query object
        :return: List of postprocessed nodes
        """
        for post_processor in node_postprocessors:
            if hasattr(post_processor, 'postprocess_nodes'):
                if callable(getattr(post_processor, 'postprocess_nodes')):
                    nodes = post_processor.postprocess_nodes(nodes, query=query)
            if hasattr(post_processor, 'apostprocess_nodes'):
                if callable(getattr(post_processor, 'apostprocess_nodes')):
                    nodes = await post_processor.apostprocess_nodes(nodes, query=query)
        return nodes


    async def insert(
        self,
        document: RagflowDocument
    ) -> int:
        """
        Insert a file into the index group
        :param document: The document to insert
        :return: The token cost to insert the file
        """
        if hasattr(self._index, 'insert_document'):
            return await self._index.insert_document(document=document)
        return 0




    async def convert(self, group_model: GroupsModel, file: ContentUploadConfig) -> Any:
        """
        Convert an UNPROCESSED file into a compatible bundle
        :param group_model: The group the file will belong to
        :param file: The unprocessed file
        :return: The new, processed file
        """
        # Implement conversion logic for Ragflow/Elasticsearch
        raise NotImplementedError

    async def initialize(self, is_new: bool) -> None:
        """
        Initialize the index
        :param is_new: If the index is new, this signals we should create it
        :return: None
        """
        # Implement initialization logic for Ragflow/Elasticsearch
        raise NotImplementedError


    @property
    def service_config(self) -> ServiceConfig:
        """
        Get the service configuration for the current index
        :return: The service config
        """
        return self._service_config



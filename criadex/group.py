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
import time
from typing import List

from criadex.index.base_api import CriadexIndexAPI
from criadex.index.ragflow_objects.schemas import FILE_NAME_META_STR, FILE_GROUP_META_STR
from criadex.index.schemas import SearchConfig


class Group:
    """
    Wrapper class for an index representing a specific silo of information, known as an index "Group" in Criadex.
    This class is transient by nature, and only exists while information in the group is being accessed & shortly after.

    """

    EXPIRE_AFTER: int = int(os.environ.get("GROUP_EXPIRE_AFTER", "3600"))

    def __init__(
            self,
            *,
            name: str,
            index: CriadexIndexAPI
    ):
        """
        Initialize the group given its name & index

        :param name: The name of the group
        :param index: The index the group belongs to

        """

        self._group_name: str = name
        self._index: CriadexIndexAPI = index
        self._last_used: float = time.time()

    def _create_http_group_search_condition(self, config: SearchConfig) -> List[dict]:
        """
        Create the filter conditions for a given SearchConfig object suitable for application-layer filtering

        :param config: The search configuration
        :return: The search conditions (list of dicts)

        """

        # Create search condition array & populate with this group
        search_conditions: list[dict] = [{FILE_GROUP_META_STR: self._group_name}]

        # Extra groups can be added to the filter as well
        for group_name in set(config.extra_groups or []):

            # Prevent duplicate
            if group_name == self._group_name:
                continue

            search_conditions.append({FILE_GROUP_META_STR: group_name})

        return search_conditions

    async def search(self, config: SearchConfig):
        """
        Search the group for information given a search configuration

        :param config: The search configuration object
        :return: The response from the index

        """

        self._last_used = time.time()

        search_filter = config.search_filter or {}

        # Add the group constraint to the filter (OR semantics over groups)
        # Represented as {"should": [{FILE_GROUP_META_STR: name}, ...]}
        group_should = self._create_http_group_search_condition(config)
        existing_should = search_filter.get("should", [])
        search_filter["should"] = [*group_should, *existing_should]

        # Replace the search filter with the modded one
        config.search_filter = search_filter

        # Search the index given the generated group-constrained config
        return await self._index.search(config)

    async def remove(self, file_name: str) -> None:
        """
        Remove a file from the index group

        :param file_name: The name of the file to remove
        :return: None

        """

        # Application-layer delete using Elasticsearch client by query on metadata
        # We expect the underlying vector store to index metadata fields.
        es = getattr(self._index, "_elasticsearch_client", None)
        index_name = self._index.collection_name()
        if es is None:
            # Fallback: best-effort search to find nodes matching, then ignore since store doesn't expose delete
            return

        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {f"metadata.{FILE_GROUP_META_STR}": self._group_name}},
                        {"term": {f"metadata.{FILE_NAME_META_STR}": file_name}},
                    ]
                }
            }
        }
        await es.delete_by_query(index=index_name, body=query, conflicts="proceed", refresh=True)

    async def delete(self) -> None:
        """
        Delete the entire group from the index

        :return: None

        """

        es = getattr(self._index, "_elasticsearch_client", None)
        index_name = self._index.collection_name()
        if es is None:
            return

        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {f"metadata.{FILE_GROUP_META_STR}": self._group_name}},
                    ]
                }
            }
        }
        await es.delete_by_query(index=index_name, body=query, conflicts="proceed", refresh=True)

    @property
    def expired(self) -> bool:
        """
        Check if the group is expired (no recent uses)

        :return: Expire status

        """

        return (time.time() - self._last_used) > self.EXPIRE_AFTER

    @property
    def index(self) -> CriadexIndexAPI:
        """
        Getter for the index the group wraps

        :return: The index object

        """

        return self._index

    @property
    def name(self) -> str:
        """
        Getter for the group name

        :return: The group name

        """

        return self._group_name

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

from qdrant_client import grpc
from qdrant_client.http import models as http

from criadex.index.base_api import CriadexIndexAPI
from criadex.index.llama_objects.schemas import CriadexFile
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

    @property
    def _grpc_group_condition(self) -> grpc.Condition:
        """
        GRPC Protobuf condition matching this group for a Qdrant filter

        :return: GRPC Condition instance

        """

        return grpc.Condition(
            field=grpc.FieldCondition(
                key=CriadexFile.FILE_GROUP_META_STR,
                match=grpc.Match(text=self._group_name)
            )
        )

    @classmethod
    def _create_http_group_condition(cls, group_name: str) -> http.FieldCondition:
        """
        HTTP Pydantic condition matching any group for a Qdrant filter

        :return:

        """

        return http.FieldCondition(
            key=CriadexFile.FILE_GROUP_META_STR,
            match=http.MatchValue(value=group_name)
        )

    def _create_http_group_search_condition(self, config: SearchConfig) -> List[http.FieldCondition]:
        """
        Create the filter object for a given SearchConfig object

        :param config: The search configuration
        :return: The search conditions

        """

        # Create search condition array & populate with this group
        search_conditions: list[http.FieldCondition] = [self._create_http_group_condition(self._group_name)]

        # Extra groups can be added to the filter as well
        for group_name in set(config.extra_groups or []):

            # Prevent duplicate
            if group_name == self._group_name:
                continue

            search_conditions.append(self._create_http_group_condition(group_name))

        return search_conditions

    async def search(self, config: SearchConfig):
        """
        Search the group for information given a search configuration

        :param config: The search configuration object
        :return: The response from the index

        """

        self._last_used = time.time()

        search_filter: http.Filter = config.search_filter or http.Filter()

        # Add the group constraint to the filter
        # Important note that "SHOULD" means "OR". https://qdrant.tech/documentation/concepts/filtering/
        # Only 1 must match, which is what we use to allow child bots by matching ANY of the indexes.
        search_filter.should = [*self._create_http_group_search_condition(config), *(search_filter.should or [])]

        # Replace the search filter with the modded one
        config.search_filter = search_filter

        # Search the index given the generated group-constrained config
        return await self._index.search(config)

    async def insert(self, file: CriadexFile) -> int:
        """
        Insert a file into the index group

        :param file: The file to insert
        :return: The token cost to insert the file

        """
        return await self._index.insert(file=file)

    async def remove(self, file_name: str) -> None:
        """
        Remove a file from the index group

        :param file_name: The name of the file to remove
        :return: None

        """

        file_condition: grpc.Condition = grpc.Condition(
            field=grpc.FieldCondition(
                key=CriadexFile.FILE_NAME_META_STR,
                match=grpc.Match(keyword=file_name)
            )
        )

        await self._index.qdrant_client.async_grpc_points.Delete(
            grpc.DeletePoints(
                wait=False,
                collection_name=self._index.collection_name(),
                points=grpc.PointsSelector(
                    filter=grpc.Filter(
                        must=[self._grpc_group_condition, file_condition]
                    )
                ),
            )
        )

    async def delete(self) -> None:
        """
        Delete the entire group from the index

        :return: None

        """

        await self._index.qdrant_client.async_grpc_points.Delete(
            grpc.DeletePoints(
                wait=False,
                collection_name=self._index.collection_name(),
                points=grpc.PointsSelector(
                    filter=grpc.Filter(
                        must=[self._grpc_group_condition]
                    )
                ),
            )
        )

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

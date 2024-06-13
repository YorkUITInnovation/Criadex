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

from datetime import datetime
from typing import Optional, List

from criadex.database.schemas import Table, TableModel


class PartialGroupsModel(TableModel):
    """
    Represents a reference to an index group in the database

    """

    id: int
    name: str
    type: int
    llm_model_id: int
    embedding_model_id: int
    rerank_model_id: int


class GroupsModel(PartialGroupsModel):
    """
    Represents a reference to an index group in the database

    """

    created: datetime


class Groups(Table):
    """
    Represents an index in the database

    """

    async def insert(
            self,
            name: str,
            type: int,
            llm_model_id: int,
            embedding_model_id: int,
            rerank_model_id: int
    ) -> int:
        """
        Insert a reference to an index group in the database

        :param name: The name of the index group group
        :param type: The type of index group
        :param llm_model_id: The ID of the LLM model associated
        :param embedding_model_id: The ID of the Embedding model associated
        :param rerank_model_id: Model used for reranking
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO `Groups` (`name`, `type`, `llm_model_id`, `embedding_model_id`, `rerank_model_id`) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (name, type, llm_model_id, embedding_model_id, rerank_model_id)
            )

            return cursor.lastrowid

    async def delete(self, name: str) -> None:
        """
        Delete an index from the database

        :param name: The name of the index group
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM `Groups` WHERE `name`=%s",
                (name,)
            )

    async def retrieve_many_by_ids(self, *index_ids: List[int]) -> List[GroupsModel]:
        """
        Retrieve a number of indexes given their ID

        :param index_ids: The IDs of the index groups
        :return: A list of 'em

        """

        if len(index_ids) < 1:
            return []

        indexes: List[GroupsModel] = []
        placeholders = ', '.join(['%s'] * len(index_ids))

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {GroupsModel.to_query_str()} "
                "FROM `Groups` "
                f"WHERE `id` in ({placeholders})",
                index_ids
            )

            results: Optional[tuple] = await cursor.fetchall()

            for result in results:
                indexes.append(
                    GroupsModel.from_results(result)
                )

        return indexes

    async def retrieve(self, name: str) -> Optional[GroupsModel]:
        """
        Retrieve an index reference from the database

        :param name: The name of the index group
        :return: The retrieved index data

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {GroupsModel.to_query_str()} "
                "FROM `Groups` "
                "WHERE `name`=%s",
                (name,)
            )

            return GroupsModel.from_results(
                await cursor.fetchone()
            )

    async def exists(self, name: str) -> bool:
        """
        Check if an index exists given its name

        :param name: The name of the index group
        :return: Whether the index group exists in the database

        """

        return bool(await self.retrieve(name=name))

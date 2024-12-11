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
from typing import Optional, Tuple, List

from criadex.database.schemas import Table, TableModel


class DocumentsModel(TableModel):
    """
    A document in the index group

    """

    id: int
    name: str
    group_id: int
    created: datetime


class Documents(Table):
    """
    Represents a document in the database

    """

    async def insert(self, group_id: int, document_name: str) -> None:
        """
        Insert a document reference into the database

        :param group_id: the index group's primary key
        :param document_name: The name of the document
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO Documents (`group_id`, `name`) VALUES (%s, %s)",
                (group_id, document_name)
            )

    async def delete(self, group_id: int, document_name: str) -> None:
        """
        Delete a document reference from the database

        :param group_id: the index group's primary key
        :param document_name: The name of the document
        :return: None
        """

        return await self.delete_many(group_id, document_name)

    async def delete_many(self, group_id: int, *document_names: str) -> None:
        """
        Delete a document reference from the database

        :param group_id: the index group's primary key
        :param document_names: The names of the documents to delete
        :return: None
        """

        placeholders: str = ', '.join(['%s'] * len(document_names))

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM Documents "
                f"WHERE `group_id`=%s AND `name` IN ({placeholders})",
                (group_id, *document_names)
            )

    async def delete_all(self, group_id: int) -> None:
        """
        Delete all document references for a given index

        :param group_id: the index group's primary key
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM Documents "
                "WHERE `group_id`=%s",
                (group_id,)
            )

    async def retrieve(self, group_id: int, document_name: str) -> Optional[DocumentsModel]:
        """
        Retrieve a document reference from the databased

        :param group_id: the index group's primary key
        :param document_name: The name of the document
        :return: Full model of the document

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {DocumentsModel.to_query_str()} "
                "FROM Documents "
                "WHERE `group_id`=%s AND `name`=%s",
                (group_id, document_name)
            )

            return DocumentsModel.from_results(
                await cursor.fetchone()
            )

    async def list(self, group_id: int) -> List[DocumentsModel]:
        """
        List the document references belonging to a given index

        :param group_id: the index group's primary key
        :return: List of document references

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {DocumentsModel.to_query_str()} "
                "FROM Documents "
                "WHERE `group_id`=%s",
                (group_id,)
            )

            results: Optional[Tuple[tuple]] = await cursor.fetchall()

        return list(
            DocumentsModel.from_results(result)
            for result in results
            if result is not None
        ) if results is not None else list()

    async def exists(self, group_id: int, document_name: str) -> bool:
        """
        Check if a given reference to an index document exists

        :param group_id: the index group's primary key
        :param document_name: The name of the document
        :return: Whether the document reference exists

        """

        return bool(await self.retrieve(group_id=group_id, document_name=document_name))

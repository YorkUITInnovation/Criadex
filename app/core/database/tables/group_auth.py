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


class GroupAuthorizationsModel(TableModel):
    """
    ORM representation of the `GroupAuthorizations` MySQL table

    """

    id: int
    group_id: int
    authorization_id: int
    created_at: datetime


class GroupAuthorizations(Table):
    """
    API to interact with the `GroupAuthorizations` MySQL table

    """

    async def insert(
        self,
        group_id: int,
        authorization_id: int
    ) -> None:
        """
        Authorize a user to manage an index group

        :param group_id: The ID of the index group group
        :param authorization_id: The ID of the authorization
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO GroupAuthorizations (`group_id`, `authorization_id`) VALUES (%s, %s)",
                (group_id, authorization_id)
            )

    async def delete_all_by_authorization_id(self, authorization_id: int) -> None:
        """
        Delete ALL authorizations for a given AUTHORIZATION

        :param authorization_id: The ID of the authorization
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM GroupAuthorizations WHERE `authorization_id`=%s",
                (authorization_id,)
            )

    async def delete_all_by_group_id(self, group_id: int) -> None:
        """
        Delete ALL authorizations for a given INDEX group

        :param group_id: The ID of the index group
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM GroupAuthorizations WHERE `group_id`=%s",
                (group_id,)
            )

    async def delete_group_authorization(self, group_id: int, authorization_id: int) -> None:
        """
        Delete ONE authorization on ONE index group

        :param group_id: The ID of the index group
        :param authorization_id: The ID of the authorization
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM GroupAuthorizations WHERE `authorization_id`=%s AND `group_id`=%s",
                (authorization_id, group_id)
            )

    async def retrieve_by_authorization_id(self, authorization_id: int) -> List[GroupAuthorizationsModel]:
        """
        Retrieve ALL index-group authorizations for a given authorization

        :param authorization_id: Authorization ID
        :return: List of all index-group authorizations the user has

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {GroupAuthorizationsModel.to_query_str()} "
                "FROM GroupAuthorizations "
                "WHERE `authorization_id`=%s",
                (authorization_id,)
            )

        results: Optional[Tuple[tuple]] = await cursor.fetchall()

        return list(
            GroupAuthorizationsModel.from_results(result)
            for result in results
            if result is not None
        ) if results is not None else list()

    async def retrieve_by_group_id(self, group_id: str) -> List[GroupAuthorizationsModel]:
        """
        Retrieve ALL index-group authorizations for a given index-group

        :param group_id: The Index-group group ID
        :return: List of index-group authorizations

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {GroupAuthorizationsModel.to_query_str()} "
                "FROM GroupAuthorizations "
                "WHERE `group_id`=%s",
                (group_id,)
            )

        results: Optional[Tuple[tuple]] = await cursor.fetchall()

        return list(
            GroupAuthorizationsModel.from_results(result)
            for result in results
            if result is not None
        ) if results is not None else list()

    async def exists(self, group_id: int, authorization_id: int) -> bool:
        """
        Check if an index-group authorization exists

        :param group_id: The ID of the index-group group
        :param authorization_id: The ID of the authorization
        :return: Whether the given authorization has access to that index-group

        """

        async with self.cursor() as cursor:

            await cursor.execute(
                "SELECT `authorization_id` "
                "FROM GroupAuthorizations "
                "WHERE `group_id`=%s AND `authorization_id`=%s",
                (group_id, authorization_id)
            )

            return bool(await cursor.fetchone())

    async def delete(self, **kwargs) -> None:
        """NOT IMPLEMENTED - Use a specific delete_by method"""
        raise NotImplementedError

    async def retrieve(self, **kwargs) -> tuple:
        """NOT IMPLEMENTED - Use a specific retrieve_by method"""
        raise NotImplementedError

    async def has_llm_access(self, authorization_id: int, llm_model_id: int) -> bool:
        """
        Check if a given authorization_id has access to a model ID.
        Access is defined as the authorization_id is authorized on an index group with the model.

        :param authorization_id: The ID of the authorization
        :param llm_model_id: The ID of the model
        :return: Whether the authorization has access to the LLM model

        """

        async with self.cursor() as cursor:

            await cursor.execute(
                "SELECT DISTINCT i.id AS group_id, i.name AS index_name "
                "FROM GroupAuthorizations ia "
                "INNER JOIN `Groups` i ON ia.group_id = i.id "
                "WHERE ia.authorization_id = %s "
                "AND i.llm_model_id = %s;",
                (authorization_id, llm_model_id)
            )

            return bool(await cursor.fetchone())

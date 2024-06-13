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
from typing import Optional

from criadex.database.schemas import Table, TableModel


class AuthorizationsModel(TableModel):
    """
    ORM representation of the `Authorizations` MySQL table

    """

    id: int
    key: str
    master: int
    created_at: datetime


class Authorizations(Table):
    """
    API class for interacting with the `Authorizations` MySQL table

    """

    async def insert(self, key: str, master: int) -> None:
        """
        Insert a key into the database

        :param key: They key value
        :param master: Whether it's a master key
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO Authorizations (`key`, `master`) VALUES (%s, %s)",
                (key, master)
            )

    async def reset(self, key: str, new_key: str) -> None:
        """
        Update an existing key in the database w/out redoing ALL the foreign key links...

        :param key: The key to update
        :param new_key: The new value for the key
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "UPDATE Authorizations "
                "SET `key`=%s "
                "WHERE `key`=%s",
                (new_key, key)
            )

    async def delete(self, key: str) -> None:
        """
        Delete a key from the database

        :param key: The API key
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM Authorizations WHERE `key`=%s",
                (key,)
            )

    async def retrieve(self, key: str) -> Optional[AuthorizationsModel]:
        """
        Retrieve the key row from the database

        :param key: The API key
        :return: The model

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {AuthorizationsModel.to_query_str()} "
                "FROM Authorizations "
                "WHERE `key`=%s",
                (key,)
            )

            return AuthorizationsModel.from_results(
                await cursor.fetchone()
            )

    async def exists(self, key: str) -> bool:
        """
        Check if an API key exists in the database

        :param key: The key
        :return: Whether it exists

        """

        return bool(await self.retrieve(key=key))

    async def master(self, key: str) -> bool:
        """
        Check if a key is a master in the database

        :param key: The key
        :return: Whether it is a master key

        """

        result: AuthorizationsModel = await self.retrieve(key=key)
        return bool(result.master) if result is not None else False



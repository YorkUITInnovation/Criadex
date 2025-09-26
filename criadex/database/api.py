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
import warnings

from aiomysql import Pool

from criadex.database.schemas import BaseDatabaseAPI
from criadex.database.tables.assets import Assets
from criadex.database.tables.models.azure import AzureModels
from criadex.database.tables.models.cohere import CohereModels
from criadex.database.tables.documents import Documents
from criadex.database.tables.groups import Groups


class GroupDatabaseAPI(BaseDatabaseAPI):
    async def shutdown(self) -> None:
        """
        Shutdown the database pool
        """
        self._pool.close()
        await self._pool.wait_closed()
    """
    API for interfacing with the index group in the database

    """

    def __init__(self, pool: Pool):
        """
        Instantiate the index group database API
        :param pool: SQL Pool

        """

        super().__init__(pool)

        self.assets: Assets = Assets(pool)
        self.documents: Documents = Documents(pool)
        self.groups: Groups = Groups(pool)
        self.azure_models: AzureModels = AzureModels(pool)
        self.cohere_models: CohereModels = CohereModels(pool)

    async def initialize(self) -> None:
        """
        Initialize the database to create tables if they don't exist

        :return: None

        """

        location: str = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )

        queries: str = open(os.path.join(location, "schema.sql"), "r", encoding="utf-8").read()

        async with self._pool.acquire() as pool:
            async with pool.cursor() as cursor:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=Warning)
                    await cursor.execute(queries)

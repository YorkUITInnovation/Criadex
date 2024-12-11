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

import logging
import os
import warnings

from aiomysql import Pool

from app.core import config
from app.core.database.tables.auth import Authorizations
from app.core.database.tables.group_auth import GroupAuthorizations
from criadex.database.schemas import BaseDatabaseAPI


class AuthDatabaseAPI(BaseDatabaseAPI):
    """
    API for interacting with the Authentication tables in the database

    """

    """The directory path of this Python module"""
    LOCATION: str = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

    def __init__(self, pool: Pool):
        """
        Initialize the table APIs

        :param pool: The MySQL pool

        """

        super().__init__(pool)
        self.authorizations: Authorizations = Authorizations(pool)
        self.group_authorizations: GroupAuthorizations = GroupAuthorizations(pool)

    async def initialize(self) -> None:
        """
        Initialize the database. If tables don't exist, create them

        :return: None

        """

        queries: str = open(os.path.join(self.LOCATION, "./schema.sql"), "r", encoding="utf-8").read()

        async with self._pool.acquire() as pool:
            async with pool.cursor() as cursor:

                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=Warning)

                    # Initialize DB
                    await cursor.execute(queries)

                # Create first master key IF one is configured
                if config.APP_INITIAL_MASTER_KEY:
                    await self.create_initial_master_key()

    async def create_initial_master_key(self) -> None:
        """
        Create the first master key

        :return: None

        """

        if await self.authorizations.exists(key=config.APP_INITIAL_MASTER_KEY):
            return

        logging.getLogger('uvicorn.error').info(
            f"Generated master API key: \"{config.APP_INITIAL_MASTER_KEY}\""
        )

        await self.authorizations.insert(
            key=config.APP_INITIAL_MASTER_KEY,
            master=True
        )


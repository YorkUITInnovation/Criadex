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

from abc import abstractmethod, ABC
from contextlib import asynccontextmanager
from typing import Optional, Tuple, Any, Dict

from aiomysql import Pool, Cursor
from pydantic import BaseModel


class Table(ABC):
    """
    Generic MySQL table supporting operations, essentially an interface.

    """

    def __init__(self, pool: Pool):
        """
        Instantiate the table

        :param pool: SQL Pool

        """

        self._pool: Pool = pool

    @asynccontextmanager
    async def cursor(self) -> Cursor:
        """
        Context manager for retrieving the cursor from the pool
        :return: Cursor instance

        """

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                yield cursor

    @abstractmethod
    async def insert(self, **kwargs) -> None:
        """
        Insert a row into the database

        :param kwargs: Overridable kwargs
        :return: None

        """

        raise NotImplementedError

    @abstractmethod
    async def delete(self, **kwargs) -> None:
        """
        Delete a row from the database

        :param kwargs: Overridable kwargs
        :return: None

        """

        raise NotImplementedError

    @abstractmethod
    async def retrieve(self, **kwargs) -> tuple:
        """
        Retrieve a row of the table from the database

        :param kwargs: Overridable kwargs
        :return: Retrieved items

        """

        raise NotImplementedError

    @abstractmethod
    async def exists(self, **kwargs) -> bool:
        """
        See if a row exists in the database

        :param kwargs: Overridable kwargs
        :return: Whether the row exists

        """

        raise NotImplementedError


class TableModel(BaseModel):
    """
    Generic MySQL table model supporting operations, essentially an interface.


    """
    @classmethod
    def get_fields(cls) -> Tuple[str]:
        """
        See the fields in the TableModel

        :return: Tuple of field names

        """

        return tuple(cls.__fields__.keys())

    @classmethod
    def to_query_str(cls) -> str:
        """
        Convert the field names into an SQL query list

        :return: String representation of field names

        """

        return ", ".join([f"`{field}`" for field in cls.get_fields()])

    @classmethod
    def to_results_dict(cls, results: Optional[Tuple[Any]]) -> Optional[Dict[str, Any]]:
        """
        Pack the results of retrieval into a K:V dict

        :param results: List of results
        :return: K:V dict containing field names mapped to values

        """

        if results is None:
            return None

        fields: tuple = cls.get_fields()

        if len(results) != len(fields):
            raise ValueError("Cannot unpack unequal length!")

        return {field: results[idx] for idx, field in enumerate(fields)}

    @classmethod
    def from_results(cls, results: Optional[Tuple[Any]]) -> Optional["TableModel"]:
        """
        Pack the results of a retrieval into the model itself

        :param results: List of results
        :return: The model

        """

        results_dict: Optional[Dict[str, Any]] = cls.to_results_dict(results)
        if results_dict is None:
            return None

        return cls(**results_dict)


class BaseDatabaseAPI:
    """
    API for interfacing with the database

    """

    def __init__(self, pool: Pool):
        """
        Instantiate the database API

        :param pool: SQL Pool

        """

        self._pool: Pool = pool

    @abstractmethod
    async def initialize(self) -> None:
        """
        Instantiate the database

        :return: None

        """

        raise NotImplementedError

    @property
    def pool(self) -> Pool:
        """
        Retrieve the pool

        :return: Pool instance

        """

        return self._pool

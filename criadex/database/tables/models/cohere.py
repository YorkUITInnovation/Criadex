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

from typing import Optional, Type, Literal

from criadex.database.schemas import TableModel, Table

"""Supported models from Azure OpenAI"""
COHERE_MODELS: Type = Literal[
    "rerank-multilingual-v2.0",
    "rerank-english-v2.0",
    "rerank-multilingual-v3.0",
    "rerank-english-v3.0",
]


class CohereModelsPartialBaseModel(TableModel):
    """
    CohereModelsPartialBaseModel

    """

    api_key: str = "your-controllers-key"


class CohereModelsBaseModel(CohereModelsPartialBaseModel):
    """
    CohereModelsBaseModel

    """

    api_model: COHERE_MODELS = "rerank-multilingual-v2.0"


class CohereModelsModel(CohereModelsBaseModel):
    """
    An Azure Model config in the database

    """

    id: int


class CohereModels(Table):
    """
    Represents an Azure Model in the database

    """

    async def update(self, config: CohereModelsModel):
        """
        Update an azure model config already in the database

        :param config: The new config
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "UPDATE CohereModels "
                "SET `api_key`=%s "
                "WHERE id=%s",
                (config.api_key, config.id)
            )

    async def insert(
            self,
            config: CohereModelsBaseModel
    ) -> CohereModelsModel:
        """
        Insert a Cohere model config into the database

        :param config: The DB base CFG Model representing an object
        :return: The ID of the created model

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO CohereModels "
                "(`api_model`, `api_key`) "
                "VALUES (%s, %s)",
                (
                    config.api_model,
                    config.api_key
                )
            )

            return CohereModelsModel(**config.dict(), **{"id": cursor.lastrowid})

    async def delete(self, model_id: int) -> None:
        """
        Delete a cohere model config from the database

        :param model_id: the index group (primary key id) the model config belongs to
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM CohereModels "
                "WHERE `id`=%s",
                (model_id,)
            )

    async def retrieve(self, model_id: int) -> Optional[CohereModelsModel]:
        """
        Retrieve a Cohere Model config from the database

        :param model_id: The model ID
        :return: The model config

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {CohereModelsModel.to_query_str()} "
                "FROM CohereModels "
                "WHERE `id`=%s",
                (model_id,)
            )

            return CohereModelsModel.from_results(
                await cursor.fetchone()
            )

    async def exists(self, model_id: int) -> bool:
        """
        Check if a given model config exists in the database

        :param model_id: the index group (primary key id) the model config belongs to
        :return: Whether the model config exists

        """

        return bool(await self.retrieve(model_id=model_id))

    async def in_use(self, model_id: int) -> bool:
        """
        Check whether a given model ID is in use

        :param model_id: The ID of the model
        :return: Whether it's being used

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT 1 "
                "FROM `Groups` "
                "WHERE `rerank_model_id`=%s",
                (model_id,)
            )

            return bool(await cursor.fetchone())

    async def get_model_id(self, api_key: str, api_model: str) -> Optional[int]:
        """
        Retrieve the model ID of a model given a deployment name.
        Note that api_deployment and api_resource form a COMPOSITE UNIQUE!

        :param api_key: The model's API key
        :param api_model: The model to check
        :return: The model ID if one exists

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT id "
                "FROM CohereModels "
                "WHERE `api_key`=%s AND `api_model`=%s",
                (api_key, api_model)
            )

            result: Optional[tuple] = await cursor.fetchone()
            return result[0] if result else None

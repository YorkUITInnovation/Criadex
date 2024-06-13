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
AZURE_MODELS: Type = Literal[
    "gpt-35-turbo",
    "gpt-35-turbo-16k",
    "gpt-4",
    "gpt-4-32k",
    "text-embedding-ada-002",
    "text-embedding-ada-001",
    "text-embedding-3-large",
    "text-embedding-3-small"
]


class AzureModelsPartialBaseModel(TableModel):
    """
    AzureModelsPartialBaseModel

    """

    api_resource: str = "your-resource"
    api_version: str = "2023-05-15"
    api_key: str = "your-controllers-key"
    api_deployment: str = "your-deployment-name"


class AzureModelsBaseModel(AzureModelsPartialBaseModel):
    """
    AzureModelsBaseModel

    """

    api_model: AZURE_MODELS = "text-embedding-ada-002"


class AzureModelsModel(AzureModelsBaseModel):
    """
    An Azure Model config in the database

    """

    id: int = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def api_base(self) -> str:
        """
        API base URL (built from the api_resource)

        :return: Base URL

        """

        return f"https://{self.api_resource}.openai.azure.com"

    @property
    def additional_kwargs(self) -> dict:
        """
        Kwargs for LlamaIndex

        :return: Kwarg dictionary

        """

        return {
            "api_key": self.api_key,
            "api_base": self.api_base,
            "api_version": self.api_version
        }


class AzureModels(Table):
    """
    Represents an Azure Model in the database

    """

    async def update(self, config: AzureModelsModel):
        """
        Update an azure model config already in the database

        :param config: The new config
        :return: None

        """

        async with self.cursor() as cursor:

            await cursor.execute(
                "UPDATE AzureModels "
                "SET `api_resource`=%s, `api_version`=%s, `api_key`=%s, `api_deployment`=%s "
                "WHERE id=%s",
                (config.api_resource, config.api_version, config.api_key, config.api_deployment, config.id)
            )

    async def insert(
        self,
        config: AzureModelsBaseModel
    ) -> AzureModelsModel:
        """
        Insert an azure model config into the database

        :param config: The DB base CFG Model representing an object
        :return: The ID of the created model

        """

        async with self.cursor() as cursor:

            await cursor.execute(
                "INSERT INTO AzureModels "
                "(`api_resource`, `api_version`, `api_key`, `api_deployment`, `api_model`) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    config.api_resource,
                    config.api_version,
                    config.api_key,
                    config.api_deployment,
                    config.api_model
                )
            )

            return AzureModelsModel(**config.dict(), **{"id": cursor.lastrowid})

    async def delete(self, model_id: int) -> None:
        """
        Delete an azure model config from the database

        :param model_id: the index group (primary key id) the model config belongs to
        :return: None

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM AzureModels "
                "WHERE `id`=%s",
                (model_id,)
            )

    async def retrieve(self, model_id: int) -> Optional[AzureModelsModel]:
        """
        Retrieve an Azure Model config from the database

        :param model_id: The model ID
        :return: The model config

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT {AzureModelsModel.to_query_str()} "
                "FROM AzureModels "
                "WHERE `id`=%s",
                (model_id,)
            )

            return AzureModelsModel.from_results(
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
                "WHERE `llm_model_id`=%s OR `embedding_model_id`=%s",
                (model_id, model_id)
            )

            return bool(await cursor.fetchone())

    async def get_model_id(self, api_deployment: str, api_resource: str) -> Optional[int]:
        """
        Retrieve the model ID of a model given a deployment name.
        Note that api_deployment and api_resource form a COMPOSITE UNIQUE!

        :param api_deployment: Azure deployment name
        :param api_resource: Azure resource name
        :return: The model ID if one exists

        """

        async with self.cursor() as cursor:
            await cursor.execute(
                f"SELECT id "
                "FROM AzureModels "
                "WHERE `api_deployment`=%s AND `api_resource`=%s",
                (api_deployment, api_resource)
            )

            result: Optional[tuple] = await cursor.fetchone()
            return result[0] if result else None




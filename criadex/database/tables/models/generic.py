import json
from typing import Optional, Any, Dict

from pydantic import Field

from criadex.database.schemas import TableModel, Table


class GenericModelsBaseModel(TableModel):
    """Base model for generic provider config."""

    provider_type: str = "ollama"
    config: Dict[str, Any] = Field(default_factory=dict)


class GenericModelsModel(GenericModelsBaseModel):
    """Generic model with id."""

    id: Optional[int] = None


class GenericModels(Table):
    """Represents a generic (multi-provider) model in the database."""

    async def insert(
        self,
        config: GenericModelsBaseModel
    ) -> GenericModelsModel:
        async with self.cursor() as cursor:
            config_json = json.dumps(config.config) if config.config else "{}"
            await cursor.execute(
                "INSERT INTO GenericModels (`provider_type`, `config`) VALUES (%s, %s)",
                (config.provider_type, config_json)
            )
            row_id = cursor.lastrowid
        return GenericModelsModel(
            id=row_id,
            provider_type=config.provider_type,
            config=config.config or {}
        )

    async def update(self, model_id: int, config: Dict[str, Any]) -> GenericModelsModel:
        async with self.cursor() as cursor:
            config_json = json.dumps(config)
            await cursor.execute(
                "UPDATE GenericModels SET `config`=%s WHERE `id`=%s",
                (config_json, model_id)
            )
        return await self.retrieve(model_id=model_id)

    async def delete(self, model_id: int) -> None:
        async with self.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM GenericModels WHERE `id`=%s",
                (model_id,)
            )

    async def retrieve(self, model_id: int) -> Optional[GenericModelsModel]:
        async with self.cursor() as cursor:
            await cursor.execute(
                "SELECT `id`, `provider_type`, `config`, `created` FROM GenericModels WHERE `id`=%s",
                (model_id,)
            )
            row = await cursor.fetchone()
        if not row:
            return None
        config = row[2]
        if isinstance(config, str):
            config = json.loads(config)
        return GenericModelsModel(id=row[0], provider_type=row[1], config=config)

    async def exists(self, model_id: int) -> bool:
        return bool(await self.retrieve(model_id=model_id))

    async def get_all(self) -> list[GenericModelsModel]:
        async with self.cursor() as cursor:
            await cursor.execute(
                "SELECT `id`, `provider_type`, `config`, `created` FROM GenericModels"
            )
            rows = await cursor.fetchall()

        models: list[GenericModelsModel] = []
        for row in rows:
            config = row[2]
            if isinstance(config, str):
                config = json.loads(config)
            models.append(
                GenericModelsModel(id=row[0], provider_type=row[1], config=config)
            )
        return models

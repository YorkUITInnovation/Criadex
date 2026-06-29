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

    async def find_by_provider_and_api_model(
        self,
        provider_type: str,
        api_model: str,
    ) -> Optional[GenericModelsModel]:
        if not api_model:
            return None

        async with self.cursor() as cursor:
            await cursor.execute(
                """
                SELECT `id`, `provider_type`, `config`, `created`
                FROM GenericModels
                WHERE `provider_type` = %s
                  AND JSON_UNQUOTE(JSON_EXTRACT(`config`, '$.api_model')) = %s
                ORDER BY `id` ASC
                LIMIT 1
                """,
                (provider_type.lower(), api_model),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        config = row[2]
        if isinstance(config, str):
            config = json.loads(config)
        return GenericModelsModel(id=row[0], provider_type=row[1], config=config)

    async def find_all_by_provider_and_api_model(
        self,
        provider_type: str,
        api_model: str,
    ) -> list[GenericModelsModel]:
        if not api_model:
            return []

        async with self.cursor() as cursor:
            await cursor.execute(
                """
                SELECT `id`, `provider_type`, `config`, `created`
                FROM GenericModels
                WHERE `provider_type` = %s
                  AND JSON_UNQUOTE(JSON_EXTRACT(`config`, '$.api_model')) = %s
                ORDER BY `id` ASC
                """,
                (provider_type.lower(), api_model),
            )
            rows = await cursor.fetchall()

        models: list[GenericModelsModel] = []
        for row in rows:
            config = row[2]
            if isinstance(config, str):
                config = json.loads(config)
            models.append(GenericModelsModel(id=row[0], provider_type=row[1], config=config))
        return models

    async def dedupe_duplicates(
        self,
        provider_type: Optional[str] = None,
        api_model: Optional[str] = None,
    ) -> dict[str, int]:
        if provider_type and api_model:
            duplicate_keys = [(provider_type.lower(), api_model)]
        else:
            async with self.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT `provider_type`,
                           JSON_UNQUOTE(JSON_EXTRACT(`config`, '$.api_model')) AS api_model
                    FROM GenericModels
                    WHERE JSON_UNQUOTE(JSON_EXTRACT(`config`, '$.api_model')) IS NOT NULL
                      AND JSON_UNQUOTE(JSON_EXTRACT(`config`, '$.api_model')) != ''
                    GROUP BY `provider_type`, api_model
                    HAVING COUNT(*) > 1
                    """
                )
                duplicate_keys = await cursor.fetchall()

        merged_groups = 0
        deleted_models = 0

        for ptype, model_name in duplicate_keys:
            models = await self.find_all_by_provider_and_api_model(ptype, model_name)
            if len(models) <= 1:
                continue

            canonical_id = models[0].id
            duplicate_ids = [model.id for model in models[1:] if model.id is not None]

            async with self.cursor() as cursor:
                for duplicate_id in duplicate_ids:
                    for column in ("llm_model_id", "embedding_model_id", "rerank_model_id"):
                        await cursor.execute(
                            f"UPDATE `Groups` SET `{column}`=%s WHERE `{column}`=%s",
                            (canonical_id, duplicate_id),
                        )
                    await cursor.execute(
                        "DELETE FROM GenericModels WHERE `id`=%s",
                        (duplicate_id,),
                    )

            merged_groups += 1
            deleted_models += len(duplicate_ids)

        return {
            "merged_groups": merged_groups,
            "deleted_models": deleted_models,
        }

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

    async def find_by_ragflow_key(
        self,
        tenant_id: str,
        llm_factory: str,
        llm_name: str,
    ) -> Optional[GenericModelsModel]:
        async with self.cursor() as cursor:
            await cursor.execute(
                """
                SELECT `id`, `provider_type`, `config`, `created`
                FROM GenericModels
                WHERE `provider_type` = 'ragflow'
                  AND JSON_UNQUOTE(JSON_EXTRACT(`config`, '$.tenant_id')) = %s
                  AND JSON_UNQUOTE(JSON_EXTRACT(`config`, '$.llm_factory')) = %s
                  AND JSON_UNQUOTE(JSON_EXTRACT(`config`, '$.llm_name')) = %s
                ORDER BY `id` ASC
                LIMIT 1
                """,
                (tenant_id, llm_factory, llm_name),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        config = row[2]
        if isinstance(config, str):
            config = json.loads(config)
        return GenericModelsModel(id=row[0], provider_type=row[1], config=config)

    async def delete_ragflow_not_in_ids(self, tenant_id: str, keep_ids: set[int]) -> int:
        models = await self.get_all()
        removed = 0
        for model in models:
            if (model.provider_type or "").lower() != "ragflow":
                continue
            config = model.config or {}
            if (config.get("tenant_id") or "") != tenant_id:
                continue
            if model.id is None or model.id in keep_ids:
                continue
            await self.delete(model.id)
            removed += 1
        return removed

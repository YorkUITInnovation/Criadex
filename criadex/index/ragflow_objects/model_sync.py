"""
Sync Ragflow tenant LLM configuration into Criadex generic model registry.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import aiomysql

from criadex.database.api import GroupDatabaseAPI
from criadex.database.tables.models.generic import GenericModelsBaseModel
from criadex.models.usability import infer_model_type

logger = logging.getLogger(__name__)

RAGFLOW_DB_HOST = os.getenv("RAGFLOW_DB_HOST", "mysql")
RAGFLOW_DB_USER = os.getenv("RAGFLOW_DB_USER", "root")
RAGFLOW_DB_PASSWORD = os.getenv("RAGFLOW_DB_PASSWORD", "cria")
RAGFLOW_DB_NAME = os.getenv("RAGFLOW_DB_NAME", "rag_flow")
RAGFLOW_TENANT_ID = os.getenv("RAGFLOW_TENANT_ID", "").strip()


async def _fetch_tenant_llm_rows(tenant_id: str) -> list[dict[str, Any]]:
    connection = await aiomysql.connect(
        host=RAGFLOW_DB_HOST,
        user=RAGFLOW_DB_USER,
        password=RAGFLOW_DB_PASSWORD,
        db=RAGFLOW_DB_NAME,
    )
    try:
        cursor = await connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT tenant_id, llm_factory, llm_name, model_type, max_tokens, status
                FROM tenant_llm
                WHERE tenant_id = %s AND status = '1'
                ORDER BY llm_factory ASC, llm_name ASC
                """,
                (tenant_id,),
            )
            rows = await cursor.fetchall()
        finally:
            await cursor.close()
    finally:
        connection.close()

    output: list[dict[str, Any]] = []
    for row in rows:
        output.append(
            {
                "tenant_id": row[0],
                "llm_factory": row[1],
                "llm_name": row[2],
                "model_type": row[3] or "chat",
                "max_tokens": int(row[4] or 0),
                "status": row[5] or "1",
            }
        )
    return output


async def sync_ragflow_models(
    mysql_api: GroupDatabaseAPI,
    tenant_id: Optional[str] = None,
) -> dict[str, int]:
    """
    Mirror Ragflow tenant_llm rows into GenericModels with provider_type=ragflow.

    Returns counters: created, updated, removed, skipped.
    """
    tenant = (tenant_id or RAGFLOW_TENANT_ID).strip()
    result = {"created": 0, "updated": 0, "removed": 0, "skipped": 0}

    if not tenant:
        logger.warning("RAGFLOW_TENANT_ID is not configured; skipping Ragflow model sync.")
        return result

    try:
        tenant_rows = await _fetch_tenant_llm_rows(tenant)
    except Exception as exc:
        logger.error("Failed to read Ragflow tenant_llm for tenant %s: %s", tenant, exc, exc_info=True)
        raise

    seen_ids: set[int] = set()

    for row in tenant_rows:
        llm_name = (row.get("llm_name") or "").strip()
        llm_factory = (row.get("llm_factory") or "").strip()
        if not llm_name or not llm_factory:
            result["skipped"] += 1
            continue

        model_type = infer_model_type("ragflow", llm_name, {"model_type": row.get("model_type")})
        config = {
            "api_model": llm_name,
            "llm_name": llm_name,
            "llm_factory": llm_factory,
            "model_type": model_type,
            "tenant_id": tenant,
            "max_tokens": row.get("max_tokens") or 0,
            "status": row.get("status") or "1",
            "source": "ragflow_tenant_llm",
        }

        existing = await mysql_api.generic_models.find_by_ragflow_key(
            tenant_id=tenant,
            llm_factory=llm_factory,
            llm_name=llm_name,
        )

        if existing and existing.id is not None:
            await mysql_api.generic_models.update(existing.id, config)
            seen_ids.add(existing.id)
            result["updated"] += 1
            continue

        inserted = await mysql_api.generic_models.insert(
            GenericModelsBaseModel(provider_type="ragflow", config=config)
        )
        if inserted.id is not None:
            seen_ids.add(inserted.id)
        result["created"] += 1

    removed = await mysql_api.generic_models.delete_ragflow_not_in_ids(
        tenant_id=tenant,
        keep_ids=seen_ids,
    )
    result["removed"] = removed
    return result

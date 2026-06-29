"""
Resolve Ragflow model identifiers from tenant configuration.

Ragflow >=0.26 expects fully qualified model ids in the form
``<model_name>@<provider_instance>@<provider_factory>`` (for example the value
stored on ``tenant.llm_id``). Nothing in this module hardcodes a provider or
model name — values are read from the Ragflow database or from already-qualified
ids present in synced generic-model config.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

RAGFLOW_DB_HOST = os.getenv("RAGFLOW_DB_HOST", "mysql")
RAGFLOW_DB_USER = os.getenv("RAGFLOW_DB_USER", "root")
RAGFLOW_DB_PASSWORD = os.getenv("RAGFLOW_DB_PASSWORD", "cria")
RAGFLOW_DB_NAME = os.getenv("RAGFLOW_DB_NAME", "rag_flow")
RAGFLOW_TENANT_ID = os.getenv("RAGFLOW_TENANT_ID", "").strip()

# Ragflow's OpenAI-compatible chat completions endpoint accepts this sentinel and
# substitutes the dialog's configured ``llm_id`` (see openai_api.py in Ragflow).
RAGFLOW_COMPLETION_MODEL_PLACEHOLDER = "model"

_TENANT_DEFAULT_COLUMNS: dict[str, str] = {
    "chat": "llm_id",
    "embedding": "embd_id",
    "rerank": "rerank_id",
    "speech2text": "asr_id",
    "image2text": "img2txt_id",
    "tts": "tts_id",
}


def is_qualified_ragflow_model_id(value: str) -> bool:
    """Return True when ``value`` looks like a full Ragflow model identifier."""
    parts = [part.strip() for part in (value or "").split("@") if part.strip()]
    return len(parts) >= 3


def model_name_from_ragflow_id(ragflow_id: str) -> str:
    return (ragflow_id or "").split("@", 1)[0].strip()


async def resolve_tenant_id(*, api_key: Optional[str] = None) -> str:
    """Resolve the Ragflow tenant id from env or the API key mapping table."""
    if RAGFLOW_TENANT_ID:
        return RAGFLOW_TENANT_ID

    key = (api_key or os.getenv("RAGFLOW_API_KEY", "")).strip()
    if not key:
        return ""

    try:
        import aiomysql

        connection = await aiomysql.connect(
            host=RAGFLOW_DB_HOST,
            user=RAGFLOW_DB_USER,
            password=RAGFLOW_DB_PASSWORD,
            db=RAGFLOW_DB_NAME,
        )
        try:
            cursor = await connection.cursor()
            await cursor.execute(
                "SELECT tenant_id FROM api_token WHERE token = %s LIMIT 1",
                (key,),
            )
            row = await cursor.fetchone()
            await cursor.close()
            if row and row[0]:
                return str(row[0])
        finally:
            connection.close()
    except Exception as exc:
        logger.warning("Could not resolve Ragflow tenant id from API key: %s", exc)

    return ""


async def resolve_tenant_default_model_id(
    tenant_id: str,
    *,
    model_kind: str = "chat",
) -> Optional[str]:
    """Read the tenant's default model id for ``model_kind`` from ``tenant``."""
    tenant = (tenant_id or "").strip()
    if not tenant:
        return None

    column = _TENANT_DEFAULT_COLUMNS.get(model_kind, "llm_id")
    if column not in _TENANT_DEFAULT_COLUMNS.values():
        column = "llm_id"

    try:
        import aiomysql

        connection = await aiomysql.connect(
            host=RAGFLOW_DB_HOST,
            user=RAGFLOW_DB_USER,
            password=RAGFLOW_DB_PASSWORD,
            db=RAGFLOW_DB_NAME,
        )
        try:
            cursor = await connection.cursor()
            await cursor.execute(
                f"SELECT {column} FROM tenant WHERE id = %s LIMIT 1",
                (tenant,),
            )
            row = await cursor.fetchone()
            await cursor.close()
            value = (row[0] or "").strip() if row and row[0] else ""
            if is_qualified_ragflow_model_id(value):
                return value
        finally:
            connection.close()
    except Exception as exc:
        logger.warning(
            "Could not resolve Ragflow tenant default %s for tenant %s: %s",
            column,
            tenant,
            exc,
        )

    return None


async def _lookup_provider_model_id(
    tenant_id: str,
    *,
    model_name: str,
    model_kind: str,
    llm_factory: str = "",
) -> Optional[str]:
    """Look up a qualified id from Ragflow v0.26 provider tables when present."""
    try:
        import aiomysql

        connection = await aiomysql.connect(
            host=RAGFLOW_DB_HOST,
            user=RAGFLOW_DB_USER,
            password=RAGFLOW_DB_PASSWORD,
            db=RAGFLOW_DB_NAME,
        )
        try:
            cursor = await connection.cursor()
            params: list[str] = [tenant_id, model_name, model_kind]
            factory_clause = ""
            if llm_factory:
                factory_clause = " AND tmp.provider_name = %s"
                params.append(llm_factory)

            await cursor.execute(
                f"""
                SELECT tm.model_name, tmi.instance_name, tmp.provider_name
                FROM tenant_model tm
                JOIN tenant_model_instance tmi ON tm.instance_id = tmi.id
                JOIN tenant_model_provider tmp ON tm.provider_id = tmp.id
                WHERE tmp.tenant_id = %s
                  AND tm.model_name = %s
                  AND tm.model_type = %s
                  {factory_clause}
                LIMIT 1
                """,
                tuple(params),
            )
            row = await cursor.fetchone()
            await cursor.close()
            if not row:
                return None
            full_id = f"{row[0]}@{row[1]}@{row[2]}"
            if is_qualified_ragflow_model_id(full_id):
                return full_id
        finally:
            connection.close()
    except Exception as exc:
        logger.debug("Provider-model lookup unavailable for %s: %s", model_name, exc)

    return None


async def resolve_qualified_model_id(
    *,
    api_model: str,
    llm_factory: str = "",
    model_kind: str = "chat",
    tenant_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve a Ragflow-qualified model id for API calls.

    Returns a fully qualified id when one can be determined from config or tenant
    data. Returns ``None`` when the caller should omit the field and let Ragflow
    apply the tenant default.
    """
    candidate = (api_model or "").strip()
    if not candidate:
        return None
    if is_qualified_ragflow_model_id(candidate):
        return candidate

    tenant = (tenant_id or await resolve_tenant_id(api_key=api_key)).strip()
    if not tenant:
        return None

    default_id = await resolve_tenant_default_model_id(tenant, model_kind=model_kind)
    if default_id and model_name_from_ragflow_id(default_id) == candidate:
        factory = (llm_factory or "").strip()
        if not factory or default_id.rsplit("@", 1)[-1] == factory:
            return default_id

    provider_id = await _lookup_provider_model_id(
        tenant,
        model_name=candidate,
        model_kind=model_kind,
        llm_factory=(llm_factory or "").strip(),
    )
    if provider_id:
        return provider_id

    return None

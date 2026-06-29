"""
Helpers for deciding which Criadex registry models are configured and usable.
"""

from __future__ import annotations

from typing import Any, Optional

from criadex.database.tables.models.azure import AzureModelsModel
from criadex.database.tables.models.cohere import CohereModelsModel
from criadex.database.tables.models.generic import GenericModelsModel

_PLACEHOLDER_API_KEYS = {"", "your-controllers-key"}
_PLACEHOLDER_API_RESOURCE_PREFIX = "your-resource"
_PLACEHOLDER_DEPLOYMENT_PREFIX = "your-deployment"


def _normalize_model_type(raw: Optional[str]) -> str:
    value = (raw or "").strip().lower()
    if value in {"embedding", "embed"}:
        return "embedding"
    if value == "rerank":
        return "rerank"
    if value in {"chat", "image2text", "speech2text", "tts"}:
        return "chat"
    return value


def infer_model_type(
    provider_type: str,
    api_model: Optional[str],
    config: Optional[dict[str, Any]] = None,
) -> str:
    config = config or {}
    explicit = _normalize_model_type(config.get("model_type"))
    if explicit:
        return explicit

    provider = (provider_type or "").lower()
    name = (api_model or "").lower()

    if provider == "cohere" or "rerank" in name:
        return "rerank"
    if "embedding" in name or "embed" in name:
        return "embedding"
    return "chat"


def is_azure_model_usable(model: AzureModelsModel) -> bool:
    resource = (model.api_resource or "").strip()
    deployment = (model.api_deployment or "").strip()
    api_key = (model.api_key or "").strip()

    if resource.startswith(_PLACEHOLDER_API_RESOURCE_PREFIX):
        return False
    if deployment.startswith(_PLACEHOLDER_DEPLOYMENT_PREFIX):
        return False
    if api_key in _PLACEHOLDER_API_KEYS:
        return False
    return True


def is_cohere_model_usable(model: CohereModelsModel) -> bool:
    api_key = (model.api_key or "").strip()
    return api_key not in _PLACEHOLDER_API_KEYS


def is_generic_model_usable(model: GenericModelsModel) -> bool:
    config = model.config or {}
    api_model = (config.get("api_model") or "").strip()
    if not api_model:
        return False

    provider = (model.provider_type or "").lower()
    if provider == "ragflow":
        # Synced from active tenant_llm rows in Ragflow.
        return (config.get("status") or "1") == "1"

    api_base = (config.get("api_base_url") or config.get("api_base") or "").strip()
    if provider in {"ollama", "openai", "anthropic"}:
        return bool(api_base)
    return True

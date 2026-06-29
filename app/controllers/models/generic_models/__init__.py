"""
Generic models router for multi-provider support (ollama, openai, anthropic, etc.).
Registered last so /models/azure/* and /models/cohere/* take precedence.
"""

from fastapi import Security

from app.core.security import get_api_key_model_query
from app.core import config
from app.core.route import CriaRouter
from app.core.schemas import AppMode
from . import about, create, delete, update, list

router = CriaRouter(
    tags=["Models:Generic"],
    dependencies=[Security(get_api_key_model_query)] if config.APP_MODE == AppMode.PRODUCTION else []
)

router.include_views(
    create.view,
    update.view,
    delete.view,
    about.view,
    list.view,
)

__all__ = ["router"]

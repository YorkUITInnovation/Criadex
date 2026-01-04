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

from fastapi import Security

from app.core.security import get_api_key_model_query
from app.core import config
from app.core.schemas import AppMode
from .ragflow_agents.chat import router as chat_router
from .ragflow_agents.intents import router as intents_router
from .ragflow_agents.language import router as language_router
from .ragflow_agents.related_prompts import router as related_prompts_router
from .ragflow_agents.transform import router as transform_router
from ...core.route import CriaRouter

router = CriaRouter(
    dependencies=[Security(get_api_key_model_query)] if config.APP_MODE == AppMode.PRODUCTION else []
)

router.include_views(
    chat_router,
    intents_router,
    language_router,
    related_prompts_router,
    transform_router,
)

__all__ = ["router"]

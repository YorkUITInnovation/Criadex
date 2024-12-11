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
from app.core.route import CriaRouter
from app.core.schemas import AppMode
from . import chat, intents, language, transform, related_prompts

router = CriaRouter(
    tags=["Agents:Azure"],
    dependencies=[Security(get_api_key_model_query)] if config.APP_MODE == AppMode.PRODUCTION else []
)

router.include_views(
    chat.view,
    intents.view,
    language.view,
    transform.view,
    related_prompts.view
)

__all__ = ["router"]

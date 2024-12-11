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

from app.core.security import get_api_key_master
from app.core import config
from app.core.schemas import AppMode
from app.core.route import CriaRouter
from . import check, create, delete, list

router = CriaRouter(
    dependencies=[Security(get_api_key_master)] if config.APP_MODE == AppMode.PRODUCTION else [],
    tags=["Group Authorization"]
)

router.include_views(
    create.view,
    delete.view,
    check.view,
    list.view
)

__all__ = ["router"]

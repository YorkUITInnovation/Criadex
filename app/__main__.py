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
import warnings

# Create the regex pattern with wildcards (.* allows any characters before and after)
import uvicorn

# Disable UserWarning: "Valid config keys have changed in V2" cuz llama-index is wack
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Valid config keys have changed in V2:\n" + r"\* 'allow_population_by_field_name'"
)

from app.core import config
from app.core.schemas import AppMode

if __name__ == "__main__":
    # Import the app instance

    uvicorn.run(
        app="app.__app__:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=config.APP_MODE == AppMode.TESTING,
        workers=1,
    )

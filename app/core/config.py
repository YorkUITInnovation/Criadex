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

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from criadex.schemas import QdrantCredentials, MySQLCredentials
from .schemas import AppMode, check_env_path

ENV_PATH: str = os.environ.get('ENV_PATH', "./.env")
ENV_LOADED: bool = load_dotenv(dotenv_path=check_env_path(ENV_PATH))

APP_MODE: AppMode = AppMode[os.environ.get('APP_API_MODE', AppMode.TESTING.name)]
APP_HOST: str = "0.0.0.0"
APP_PORT: int = int(os.environ.get('APP_API_PORT', 25574))
APP_TITLE: str = "Criadex 📁"
APP_VERSION = "1.0.0"
DOCS_URL: str = "/"

# Initial Auth Key
APP_INITIAL_MASTER_KEY: Optional[str] = os.environ.get("APP_INITIAL_MASTER_KEY")

# Search Rate Limit
SEARCH_INDEX_LIMIT_MINUTE: str = (os.environ.get("SEARCH_INDEX_LIMIT_MINUTE") or "30") + "/minute"
SEARCH_INDEX_LIMIT_HOUR: str = (os.environ.get("SEARCH_INDEX_LIMIT_HOUR") or "250") + "/hour"
SEARCH_INDEX_LIMIT_DAY: str = (os.environ.get("SEARCH_INDEX_LIMIT_DAY") or "1500") + "/day"

# Query Rate Limit
QUERY_MODEL_RATE_LIMIT_MINUTE: str = SEARCH_INDEX_LIMIT_MINUTE
QUERY_MODEL_RATE_LIMIT_HOUR: str = SEARCH_INDEX_LIMIT_HOUR
QUERY_MODEL_RATE_LIMIT_DAY: str = SEARCH_INDEX_LIMIT_DAY

# Swagger Config
SWAGGER_TITLE: str = "Criadex API"
SWAGGER_FAVICON: str = "https://i.imgur.com/9XOI3qg.png"
SWAGGER_DESCRIPTION = f"""
A semantic search engine developed by [UIT Innovation](https://github.com/YorkUITInnovation) at [York University](https://yorku.ca/) with a targetted focus on generative AI for higher education.

"""

# Vector DB Config
QDRANT_CREDENTIALS: QdrantCredentials = QdrantCredentials(
    host=os.environ["QDRANT_HOST"],
    port=os.environ["QDRANT_PORT"],
    grpc_port=os.environ["QDRANT_GRPC_PORT"],
    api_key=os.environ.get("QDRANT_API_KEY")
)

# MySQL Config
MYSQL_CREDENTIALS: MySQLCredentials = MySQLCredentials(
    host=os.environ["MYSQL_HOST"],
    port=os.environ["MYSQL_PORT"],
    username=os.environ["MYSQL_USERNAME"],
    database=os.environ["MYSQL_DATABASE"],
    password=os.environ.get("MYSQL_PASSWORD"),
)

# Set the Tiktoken cache directory
os.environ["TIKTOKEN_CACHE_DIR"] = os.environ.get(
    "TIKTOKEN_CACHE_DIR",
    str(
        Path(os.environ.get("VIRTUAL_ENV", "./"))
        .joinpath("./tiktoken")
    )
)

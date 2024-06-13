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

import json

from criadex.index.index_api.document.store_index import DocumentVectorStoreIndex
from criadex.index.llama_objects.schemas import CriadexFile

QUESTION_NODE_ANSWER_KEY: str = "answer"
QUESTION_NODE_LLM_REPLY: str = "llm_reply"  # Make sure if changing to update in Criabot


class QuestionVectorStoreIndex(DocumentVectorStoreIndex):
    """
    Index vector store for questions

    """

    @classmethod
    def seed_document(cls) -> CriadexFile:
        """
        Create a seed document for a new index
        :return: The seed document

        """

        return CriadexFile.create(
            file_name="seed-file",
            text=json.dumps(["seed-question"]),
            file_group="seed-group",
            file_metadata={
                QUESTION_NODE_ANSWER_KEY: "",
                QUESTION_NODE_LLM_REPLY: False
            }
        )

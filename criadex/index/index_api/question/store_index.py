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
import datetime

from criadex.database.tables.groups import GroupsModel
from criadex.index.index_api.question.index_objects import QuestionConfig, QUESTION_NODE_ANSWER_KEY, QUESTION_NODE_LLM_REPLY
from criadex.index.schemas import Bundle, CriadexBaseIndex
from criadex.schemas import IndexType


class QuestionVectorStoreIndex(CriadexBaseIndex):
    """
    Index vector store for questions

    """

    @classmethod
    def seed_bundle(cls) -> Bundle:
        """
        Create a seed document for a new index
        :return: The seed document

        """

        return Bundle(
            name="seed-file",
            config=QuestionConfig(questions=["seed-question"], answer="seed-answer"),
            group=GroupsModel(
                id=-1,
                name="seed-group",
                type=IndexType.QUESTION.value,
                llm_model_id=-1,
                embedding_model_id=-1,
                rerank_model_id=-1,
                created=datetime.datetime.now(datetime.timezone.utc)
            ),
            metadata={
                QUESTION_NODE_ANSWER_KEY: "",
                QUESTION_NODE_LLM_REPLY: False
            },

        )

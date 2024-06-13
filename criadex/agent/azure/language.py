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

import enum
from typing import List, Optional

from lingua import LanguageDetectorBuilder, LanguageDetector, IsoCode639_1, Language
from ..base_agent import BaseAgent, BaseAgentResponse


class LanguageAgentLanguage(str, enum.Enum):
    """
    Supported list of languages for the language agent

    """

    ENGLISH = "EN"
    FRENCH = "FR"

    @classmethod
    def list(cls) -> List[str]:
        """
        List the languages as strings
        :return: The list of languages

        """

        return list(map(lambda c: c.value, cls))


class LanguageAgentResponse(BaseAgentResponse):
    """
    The response of the language agent

    """

    language: Optional[LanguageAgentLanguage]


class LanguageAgent(BaseAgent):
    """
    Determine the language of the query. Currently, this is restricted to only French and english.

    """

    SUPPORTED_LANGS: List[IsoCode639_1] = [getattr(IsoCode639_1, L) for L in LanguageAgentLanguage.list()]
    LANG_DETECTOR: LanguageDetector = LanguageDetectorBuilder.from_iso_codes_639_1(*SUPPORTED_LANGS).build()

    def execute(self, prompt: str) -> LanguageAgentResponse:
        """
        Execute the language detection agent

        :param prompt: The prompt to detect the language of
        :return: The language of the prompt

        """

        language: Optional[Language] = self.LANG_DETECTOR.detect_language_of(
            text=prompt
        )

        # Success
        if language is not None:
            return LanguageAgentResponse(
                message="Successfully ran detection inference!",
                language=language.iso_code_639_1.name
            )

        # Not one of the two
        return LanguageAgentResponse(
            message=f"Language is none of: {', '.join(LanguageAgentLanguage.list())}",
            language=None
        )

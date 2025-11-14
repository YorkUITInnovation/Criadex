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
from typing import List, Optional, Any
from pydantic import BaseModel
from lingua import LanguageDetectorBuilder

class LanguageAgentResponse(BaseModel):
    language: Optional[str]
    confidence: float

class LanguageAgent:
    def __init__(self):
        self.detector = LanguageDetectorBuilder.from_all_languages().with_preloaded_language_models().build()

    def detect(self, text: str) -> LanguageAgentResponse:
        confidence_values = self.detector.compute_language_confidence_values(text)
        if not confidence_values:
            return LanguageAgentResponse(language=None, confidence=0.0)
        
        most_likely_language = confidence_values[0]
        return LanguageAgentResponse(
            language=most_likely_language.language.iso_code_639_1.name,
            confidence=most_likely_language.value
        )
"""
@author Kiarash Bashokian
"""

import enum


class ParserStrategy(str, enum.Enum):
    """Document parsing strategies for native Ragflow upload."""

    GENERIC = "GENERIC"
    AL_SYLLABUS = "ALSYLLABUS"
    AL_SYLLABUS_FR = "ALSYLLABUSFR"
    PARAGRAPH = "PARAGRAPH"

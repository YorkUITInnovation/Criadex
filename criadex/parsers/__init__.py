"""
Local document parsers — ported from CriaParse (reference service, being retired).

These parsers pre-process DOCX files into semantic text chunks *before* uploading
to Ragflow, so that Ragflow can index natural-language syllabus content instead
of raw binary structure.

GENERIC strategy skips local parsing entirely; Ragflow's native parser is used.
"""

from criadex.parsers.models import ParserStrategy
from criadex.parsers.parse import parse_to_bytes

__all__ = ["ParserStrategy", "parse_to_bytes"]

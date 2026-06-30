"""
Paragraph DOCX parser — ported from CriaParse (reference service, being retired).

Splits a DOCX into ~325-word paragraph sections and returns them as text strings.

@author Kiarash Bashokian
"""

import io
import re
from typing import List

from docx import Document

SECTION_LENGTH = 325


def split_document(doc: Document) -> List[str]:
    paragraph_count = len(doc.paragraphs)
    if paragraph_count == 0:
        return []

    section: List[str] = []
    section_temp = doc.paragraphs[0].text

    for i in range(1, paragraph_count):
        next_temp = section_temp + " " + doc.paragraphs[i].text
        if len(next_temp.split()) <= SECTION_LENGTH:
            section_temp = next_temp
        elif (len(next_temp.split()) - SECTION_LENGTH) > (SECTION_LENGTH - len(section_temp.split())):
            section.append(section_temp)
            section_temp = doc.paragraphs[i].text
        else:
            section.append(next_temp)
            section_temp = ""

    section.append(section_temp)
    return section


def run_converter(docx: io.BytesIO) -> List[str]:
    """Split a DOCX into paragraph-length text sections."""
    doc = Document(docx)
    return [s for s in split_document(doc) if s and s.strip()]


def run_converter_text(docx: io.BytesIO) -> List[str]:
    """Alias for run_converter — returns paragraph text strings."""
    return run_converter(docx)


def run_converter_from_text(text: str, content_type: str = "text/plain") -> List[str]:
    """Split plain/markdown/html text into paragraph-length sections."""
    if content_type == "text/html":
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

    paragraphs: List[str] = []
    current: List[str] = []
    for line in text.splitlines():
        if line.strip():
            current.append(line.rstrip())
        elif current:
            paragraphs.append("\n".join(current).strip())
            current = []
    if current:
        paragraphs.append("\n".join(current).strip())

    return [p for p in paragraphs if p]

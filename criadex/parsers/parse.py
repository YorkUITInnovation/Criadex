"""
Dispatch function: pre-process file bytes using a named parser strategy.

GENERIC → raw bytes returned as-is; Ragflow's native parser handles the file.
Other strategies → parse locally, join element texts, return as UTF-8 .txt bytes.

@author Kiarash Bashokian
"""

import io
import os
from typing import Optional, Tuple

from criadex.parsers.models import ParserStrategy

_HTML_EXTENSIONS = {".html", ".htm"}
_HTML_MIME_PREFIXES = ("text/html", "application/xhtml")


def _is_html(filename: Optional[str], content_type: Optional[str]) -> bool:
    if content_type:
        ct = content_type.lower()
        if any(ct.startswith(p) for p in _HTML_MIME_PREFIXES):
            return True
    if filename:
        _, ext = os.path.splitext(filename.lower())
        return ext in _HTML_EXTENSIONS
    return False


def parse_to_bytes(
    strategy: Optional[ParserStrategy],
    file_bytes: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Tuple[bytes, str]:
    """Return (output_bytes, output_filename) for the given strategy.

    For GENERIC (or None), the raw bytes and original filename are returned unchanged
    so Ragflow can apply its own native parsing.  For all other strategies the file is
    parsed locally and the result is returned as UTF-8 text with a .txt extension.

    Exception: HTML files with GENERIC strategy are auto-routed to PARAGRAPH because
    Ragflow's native HTML parser produces 0 chunks for typical HTML content.
    """
    out_filename = filename or "upload"

    if not strategy or strategy == ParserStrategy.GENERIC:
        # Ragflow native parse produces 0 chunks for HTML — pre-process via PARAGRAPH instead.
        if _is_html(filename, content_type):
            strategy = ParserStrategy.PARAGRAPH
        else:
            return file_bytes, out_filename

    base = os.path.splitext(out_filename)[0]
    txt_filename = f"{base}.txt"
    buffer = io.BytesIO(file_bytes)

    if strategy == ParserStrategy.AL_SYLLABUS:
        from criadex.parsers.alsyllabus.conversions import convert_file
        nodes = convert_file(buffer)
        text = "\n\n---\n\n".join(n["text"] for n in nodes if n.get("text"))

    elif strategy == ParserStrategy.AL_SYLLABUS_FR:
        from criadex.parsers.alsyllabusfr.conversions import run_converter
        texts = run_converter(buffer)
        text = "\n\n---\n\n".join(t for t in texts if t and t.strip())

    elif strategy == ParserStrategy.PARAGRAPH:
        if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            from criadex.parsers.paragraph.conversions import run_converter
            texts = run_converter(buffer)
        else:
            from criadex.parsers.paragraph.conversions import run_converter_from_text
            raw = file_bytes.decode("utf-8", errors="ignore")
            texts = run_converter_from_text(raw, content_type or "text/plain")
        text = "\n\n---\n\n".join(t for t in texts if t and t.strip())

    else:
        return file_bytes, out_filename

    if not text.strip():
        return file_bytes, out_filename

    return text.encode("utf-8"), txt_filename

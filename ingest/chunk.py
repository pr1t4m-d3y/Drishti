"""Structure-aware chunking: keep section headings and clause numbers as metadata.

Regulatory text is hierarchical (Chapter > numbered paragraph > sub-clause). Fixed-size windows
split a clause from its heading and its number, which destroys the citation. Here we first split
on headings / numbered clauses, then only fall back to size-based splitting inside long clauses.
"""

from __future__ import annotations

import re

from drishti.rag.store import Chunk
from ingest.parse import Page

CHAPTER = re.compile(r"^(chapter|part|section|annex(?:ure)?|schedule)\s+[ivxlcdm\d]+[\.:\- ]*.*$", re.I)
NUMBERED = re.compile(r"^(?P<num>\d{1,3}(?:\.\d{1,3}){0,3})[\.\)]?\s+(?P<title>[A-Z].{0,140})$")
LETTERED = re.compile(r"^(?P<num>[A-Z])[\.\)]\s+(?P<title>[A-Z].{0,140})$")
MAX_CHARS, OVERLAP = 1400, 150


def _split_long(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[.;:])\s+", text)
    parts, cur = [], ""
    for s in sentences:
        if cur and len(cur) + len(s) + 1 > max_chars:
            parts.append(cur)
            cur = cur[-overlap:] + " " + s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        parts.append(cur)
    return parts


def chunk_document(doc_id: str, doc_title: str, pages: list[Page]) -> list[Chunk]:
    chapter, heading, clause = "", "", ""
    buf: list[str] = []
    buf_page = 1
    chunks: list[Chunk] = []

    def flush() -> None:
        body = " ".join(buf).strip()
        buf.clear()
        if len(body) < 40:  # drop stray fragments
            return
        section = " > ".join(x for x in (chapter, heading) if x) or "(untitled)"
        for part in _split_long(body):
            chunks.append(Chunk(doc_id, doc_title, section, clause, buf_page, part))

    for page in pages:
        for line in page.text.split("\n"):
            m_num, m_let = NUMBERED.match(line), LETTERED.match(line)
            if CHAPTER.match(line) and len(line) < 120:
                flush()
                chapter, heading, clause = line.strip(), "", ""
                buf_page = page.number
            elif m_num or m_let:
                flush()
                m = m_num or m_let
                assert m is not None
                clause, heading = m.group("num"), f"{m.group('num')}. {m.group('title').strip()}"
                buf_page = page.number
                buf.append(line)
            else:
                if not buf:
                    buf_page = page.number
                buf.append(line)
    flush()
    return chunks

"""Structure-aware chunking: keep chapter, topic heading and paragraph number as metadata.

Regulatory text is hierarchical (Chapter > lettered topic > numbered paragraph > (1)(2) sub-items). Fixed-size
windows split a paragraph from its number and heading, which destroys the citation. We split on those
boundaries first and only fall back to size-based splitting inside a very long paragraph.

Citation fields per chunk:
  section = "Chapter III – Responsible Lending Conduct > C. Penal Charges in Loan Accounts"
  clause  = "13"   (the paragraph number)
"""

from __future__ import annotations

import re

from drishti.rag.store import Chunk
from ingest.parse import Page

CHAPTER = re.compile(r"^(chapter|part|section|annex(?:ure)?|schedule)\s+[ivxlcdm\d]+[A-Za-z]?\b.*$", re.I)
PARA = re.compile(r"^(?P<num>\d{1,3}(?:\.\d{1,3}){0,3})[\.\)]\s+(?P<rest>\S.*)$")  # "13. An NBFC shall ..."
TOPIC = re.compile(r"^(?P<num>[A-Z])[\.\)]\s+(?P<title>[A-Z].{0,110})$")  # "C. Penal Charges in Loan Accounts"
MAX_CHARS, OVERLAP = 1400, 150
SHORT_TITLE = 100  # a numbered line this short, with no sentence end, is a heading, not a paragraph


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
    chapter, topic, clause = "", "", ""
    buf: list[str] = []
    buf_page = pages[0].number if pages else 1
    chunks: list[Chunk] = []

    def flush() -> None:
        body = " ".join(buf).strip()
        buf.clear()
        if len(body) < 60:  # drops stray fragments and table-of-contents lines
            return
        section = " > ".join(x for x in (chapter, topic) if x) or "(untitled)"
        for part in _split_long(body):
            chunks.append(Chunk(doc_id, doc_title, section, clause, buf_page, part))

    for page in pages:
        for line in page.text.split("\n"):
            m_para, m_topic = PARA.match(line), TOPIC.match(line)
            if CHAPTER.match(line) and len(line) < 120:
                flush()
                chapter, topic, clause = line.strip(), "", ""
                buf_page = page.number
            elif m_topic and not line.rstrip().endswith("."):
                flush()
                topic, clause = f"{m_topic.group('num')}. {m_topic.group('title').strip()}", ""
                buf_page = page.number
            elif m_para:
                flush()
                clause = m_para.group("num")
                if len(line) <= SHORT_TITLE and not line.rstrip().endswith((".", ":", ";")):
                    topic = line.strip()  # "5. Notice before recovery": numbered heading
                buf_page = page.number
                buf.append(line)
            else:
                if not buf:
                    buf_page = page.number
                buf.append(line)
    flush()
    return chunks

"""PDF -> cleaned, page-tagged text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_MULTI_SPACE = re.compile(r"[ \t]+")
_PAGE_NO = re.compile(r"^\s*(page\s*)?\d{1,3}(\s*(of|/)\s*\d{1,3})?\s*$", re.IGNORECASE)


@dataclass
class Page:
    number: int  # 1-based
    text: str


def clean_page_text(raw: str) -> str:
    """Undo PDF artefacts: hyphenated line breaks, ragged whitespace, bare page numbers."""
    text = _HYPHEN_BREAK.sub(r"\1\2", raw.replace("\r", ""))
    lines = [_MULTI_SPACE.sub(" ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln and not _PAGE_NO.match(ln)]
    return "\n".join(lines)


def strip_repeated_lines(pages: list[Page], min_pages: int = 4) -> list[Page]:
    """Drop running headers/footers: short lines that appear on most pages."""
    if len(pages) < min_pages:
        return pages
    counts: dict[str, int] = {}
    for p in pages:
        for ln in set(p.text.split("\n")):
            if len(ln) < 90:
                counts[ln] = counts.get(ln, 0) + 1
    repeated = {ln for ln, n in counts.items() if n >= max(3, int(0.6 * len(pages)))}
    return [Page(p.number, "\n".join(ln for ln in p.text.split("\n") if ln not in repeated)) for p in pages]


def parse_pdf(path: Path) -> tuple[str, list[Page]]:
    reader = PdfReader(str(path))
    title = (reader.metadata.title if reader.metadata else None) or path.stem.replace("_", " ")
    pages = [Page(i + 1, clean_page_text(p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    return str(title), strip_repeated_lines(pages)


def parse_text(path: Path) -> tuple[str, list[Page]]:
    """Plain text. Files written by `ingest fetch` start with `# Key: value` provenance lines (title, source URL,
    "no pagination"); those become the title and are not indexed. Web text has no page numbers: page 0."""
    raw = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body: list[str] = []
    for ln in raw.split("\n"):
        m = re.match(r"^#\s*(\w+):\s*(.*)$", ln) if not body else None
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
        else:
            body.append(ln)
    paginated = "no pagination" not in meta.get("format", "")
    title = meta.get("title") or path.stem.replace("_", " ")
    return title, [Page(1 if paginated else 0, clean_page_text("\n".join(body)))]

"""RBI corpus fetching, parsing, structure-aware chunking and (when present) the real corpus itself."""

import io
import json
from pathlib import Path

import pytest

from drishti.config import get_settings
from ingest import fetch
from ingest.chunk import chunk_document
from ingest.parse import parse_text
from ingest.sources import SOURCES

PAGE = """<html><head><title>Master Directions</title><script>var x = 'Chapter I';</script></head><body>
<div>Home | Notifications | Search</div>
<h2>Reserve Bank of India (Non-Banking Financial Companies &ndash; Responsible Business Conduct) Directions, 2025 (Updated as on July 1, 2026)</h2>
<p>In exercise of the powers conferred by section 45L of the Reserve Bank of India Act, 1934, the Reserve Bank issues these Directions.</p>
<p>Chapter I &ndash; Preliminary</p><p>A. Short Title and Commencement</p>
<p>1. These Directions shall be called the Responsible Business Conduct Directions, 2025.</p>
<p>2. These Directions shall become effective from the date of issuance unless indicated otherwise.</p>
<p>Chapter III &ndash; Responsible Lending Conduct</p><p>C. Penal Charges in Loan Accounts</p>
<p>13. An NBFC shall not levy penal interest; penal charges, if any, shall be reasonable and shall not be capitalised further.</p>
<p>(1) the charges shall be disclosed in the key fact statement;</p><p>(2) the same shall be displayed on the website.</p>
<div>Web Information Manager</div><div>Accessibility Statement</div></body></html>""" + " " * 6000


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_html_to_text_drops_chrome_scripts_and_footer():
    t = fetch.html_to_text(PAGE)
    assert t.startswith("In exercise of the powers") and "Home | Notifications" not in t and "var x" not in t
    assert "Web Information Manager" not in t and "Chapter III – Responsible Lending Conduct" in t
    assert "13. An NBFC shall not levy penal interest" in t


def test_page_title_is_read_from_the_page():
    assert fetch.page_title(PAGE).startswith("Reserve Bank of India (Non-Banking Financial Companies – Responsible Business Conduct) Directions, 2025")


def test_fetch_one_writes_provenance_header_and_refuses_stubs(tmp_path):
    big = PAGE.replace("<div>Web Information Manager</div>", "<p>" + "x " * 4000 + "</p><div>Web Information Manager</div>")
    src = SOURCES[0].__class__("t", 1, "Responsible Business Conduct", "t")
    entry = fetch.fetch_one(src, tmp_path, opener=lambda req, timeout: FakeResp(big.encode()))
    txt = (tmp_path / "t.txt").read_text()
    assert txt.startswith("# Source: https://rbi.org.in/") and "# Fetched:" in txt and "# Format: web text" in txt
    assert entry["sha256"] and entry["characters"] > 5000
    with pytest.raises(ValueError, match="stub"):
        fetch.fetch_one(src, tmp_path, opener=lambda req, timeout: FakeResp(b"<html>Responsible Business Conduct tiny</html>"))
    with pytest.raises(ValueError, match="layout"):
        fetch.fetch_one(src, tmp_path, opener=lambda req, timeout: FakeResp(b"<html>different page</html>"))


def test_fetched_text_parses_to_title_and_unpaginated_page(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("# Source: u\n# Title: My Directions\n# Format: web text (no pagination)\nChapter I\nbody text here\n")
    title, pages = parse_text(f)
    assert title == "My Directions" and pages[0].number == 0 and "Source" not in pages[0].text


def test_rbi_style_structure_is_kept_in_chunks(tmp_path):
    f = tmp_path / "rbi.txt"
    f.write_text("# Title: T\n# Format: web text (no pagination)\n" + fetch.html_to_text(PAGE))
    title, pages = parse_text(f)
    cs = chunk_document("rbi", title, pages)
    penal = next(c for c in cs if c.clause == "13")
    assert penal.section == "Chapter III – Responsible Lending Conduct > C. Penal Charges in Loan Accounts"
    assert "key fact statement" in penal.text and "(2) the same shall be displayed" in penal.text  # sub-items stay with their paragraph
    assert penal.page == 0
    assert {c.clause for c in cs} >= {"1", "2", "13"}


def test_sources_registry_is_wellformed():
    assert len({s.slug for s in SOURCES}) == len(SOURCES) and len({s.page_id for s in SOURCES}) == len(SOURCES)
    assert all(s.url.startswith("https://rbi.org.in/") for s in SOURCES)


CORPUS = get_settings().policies_dir
REAL = sorted(CORPUS.glob("rbi_*.txt"))


@pytest.mark.skipif(not REAL, reason="corpus not fetched (python -m ingest fetch)")
def test_real_corpus_chunks_carry_citation_metadata():
    total = 0
    for f in REAL:
        title, pages = parse_text(f)
        cs = chunk_document(f.stem, title, pages)
        total += len(cs)
        assert title.startswith("Reserve Bank of India (")
        assert len(cs) > 50
        with_clause = [c for c in cs if c.clause]
        assert len(with_clause) / len(cs) > 0.8, f"{f.name}: most chunks should carry a paragraph number"
        assert not any(c.section == "(untitled)" for c in cs)
        assert "Web Information Manager" not in "".join(c.text for c in cs)
    assert total > 500


@pytest.mark.skipif(not REAL, reason="corpus not fetched")
def test_sources_json_matches_files_on_disk():
    entries = json.loads((CORPUS / "SOURCES.json").read_text())
    assert {e["slug"] for e in entries} == {p.stem for p in REAL}
    assert all(e["url"].startswith("https://rbi.org.in/Scripts/") and e["sha256"] for e in entries)
    assert "rbi.org.in" in Path(CORPUS / "SOURCES.md").read_text()

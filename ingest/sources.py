"""The policy corpus: real, public Reserve Bank of India directions.

Each entry is the page on rbi.org.in that publishes the full text of the direction (the PDF host,
rbidocs.rbi.org.in, rejects scripted downloads, but these pages are served normally). Titles below were
read from the pages themselves on 2026-11-19; `python -m ingest fetch` re-reads and records them.
"""

from __future__ import annotations

from dataclasses import dataclass

BASE = "https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id="


@dataclass(frozen=True)
class Source:
    slug: str
    page_id: int
    expected_title: str  # sanity check: the fetched page must contain this text
    topics: str

    @property
    def url(self) -> str:
        return f"{BASE}{self.page_id}"


SOURCES: list[Source] = [
    Source("rbi_nbfc_responsible_business_conduct_2025", 12942,
           "Non-Banking Financial Companies – Responsible Business Conduct",
           "fair practices, penal charges, key fact statements, recovery agents, grievance redressal"),
    Source("rbi_nbfc_resolution_of_stressed_assets_2025", 12947,
           "Non-Banking Financial Companies – Resolution of Stressed Assets",
           "restructuring, resolution plans, early resolution, asset classification"),
    Source("rbi_nbfc_credit_cards_2025", 12956,
           "Non-Banking Financial Companies – Credit Cards: Issuance and Conduct",
           "credit card issuance, billing, interest, dues, customer protection"),
    Source("rbi_banks_resolution_of_stressed_assets_2025", 13145,
           "Commercial Banks – Resolution of Stressed Assets",
           "restructuring and resolution for commercial banks"),
    Source("rbi_banks_credit_debit_cards_2025", 13155,
           "Commercial Banks – Credit Cards and Debit Cards: Issuance and Conduct",
           "card issuance, billing, interest, recovery conduct for commercial banks"),
]

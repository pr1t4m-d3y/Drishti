# Policy corpus sources

These are **real, public** Reserve Bank of India documents. No policy text in this repository is
written by hand or by an LLM.

RBI's document server (`rbidocs.rbi.org.in`) rejects scripted downloads (it returns an HTML
bot-check page instead of the PDF), so the PDFs must be saved from a normal browser. Save each file
into this folder with the filename in the "Save as" column, then run `make ingest`.

| Save as | Document (title as printed on the RBI page) | Where to get it |
|---|---|---|
| `rbi_nbfc_responsible_business_conduct_2025.pdf` | Reserve Bank of India (Non-Banking Financial Companies – Responsible Business Conduct) Directions, 2025 (updated as on July 1, 2026): fair practices, penal charges, recovery, grievance redressal. **Primary document.** | https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12942 |
| `rbi_aifi_responsible_business_conduct_2025.pdf` | Reserve Bank of India (All India Financial Institutions – Responsible Business Conduct) Directions, 2025 (updated as on July 1, 2026). Optional, a second conduct framework to retrieve across. | https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12968 |

Each page links the main PDF (open the page, click the Directions PDF, save it from the browser).

Recommended additions so restructuring and recovery are covered explicitly. Search the title on
https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx , save the current version, and add a row above:

* RBI directions on resolution / restructuring of stressed assets applicable to your target lender type
* RBI directions on credit card and debit card issuance and conduct (the dataset is credit-card holders)
* RBI Integrated Ombudsman Scheme (grievance redressal)

Not relevant (checked): id=12669 is the Asset Reconstruction Companies Master Direction (2024).

After saving, record the issue date next to each row. The ingest manifest (`.ingest_manifest.json`)
stores every file's content hash so later changes are detected.

## Status

`data/policies/` currently contains **no PDFs**. Until they are added, policy-RAG answers and the
policy / intervention parts of the evaluation cannot be scored (the eval reports this explicitly
rather than passing).

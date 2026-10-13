# ITSM Automation & RCA Assistant

A portfolio-ready Streamlit prototype for IT Service Management teams. It demonstrates transparent rules-based incident triage, recurring-incident pattern detection, and structured Major Incident Report (MIR) drafting.

## Features
- Filter incidents by priority and service
- Summary metrics and incident-volume visualizations
- Rules-based triage suggestions with a rationale for human review
- Repeated incident summary detection by service
- MIR Markdown draft generator with timeline, root-cause, corrective-action, and preventive-action sections
- CSV downloads for triage and recurrence results
- Automated tests and GitHub Actions workflow

## Tech stack
Python, Streamlit, Pandas, Plotly, Pytest, GitHub Actions.

## Run locally (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```
Open `http://localhost:8501`.

## Run tests
```powershell
python -m pytest -q
```

## Data format
Upload a CSV with these columns:
`incident_id, created_at, service, summary, description, priority, status, resolution_minutes, business_impact`

A synthetic sample dataset is provided in `data/sample_incidents.csv`.

## Important limitations
- The triage engine is a transparent keyword/rule-based demonstration, not an approved severity classifier.
- Repeated-summary matching is basic text normalization. Similar incidents may not be detected, and matching summaries does not prove a common root cause.
- The RCA section is a human-authored hypothesis/notes field. This version does not independently establish root cause or call a generative AI API.
- Validate all generated report content before operational use.
- Do not upload or publish confidential company, customer, personal, or production incident data. Use synthetic or explicitly approved sanitized data only.

## Suggested next enhancements
1. Map rules to an approved incident policy and escalation matrix.
2. Add similarity matching and evidence-linked RCA recommendations.
3. Add action owners, due dates, and closure tracking.
4. Add optional LLM integration only after security, privacy, and governance review.

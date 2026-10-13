from __future__ import annotations

from datetime import datetime
from io import StringIO
from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).parent
DEFAULT_DATA = APP_DIR / "data" / "sample_incidents.csv"

REQUIRED_COLUMNS = {
    "incident_id", "created_at", "service", "summary", "description",
    "priority", "status", "resolution_minutes", "business_impact",
}

st.set_page_config(page_title="ITSM Automation & RCA Assistant", page_icon="🛠️", layout="wide")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def validate_data(df: pd.DataFrame) -> tuple[bool, str]:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return False, "Missing required columns: " + ", ".join(sorted(missing))
    if df.empty:
        return False, "The uploaded file contains no incident records."
    return True, ""


def classify_incident(row: pd.Series) -> dict:
    """Transparent rules-based triage. Suggestions must be validated by an incident manager."""
    text = " ".join(str(row.get(k, "")) for k in ("summary", "description", "business_impact")).lower()
    service = str(row.get("service", "")).lower()
    priority = str(row.get("priority", "")).upper().strip()
    major_terms = (
        "multiple customers", "customer-wide", "complete outage", "service unavailable",
        "production down", "critical business", "all users", "revenue impact", "data loss",
    )
    high_terms = ("degraded", "intermittent", "high latency", "unable to login", "failed transactions")
    if any(term in text for term in major_terms):
        suggested = "Potential Major Incident"
        rationale = "The incident text contains a broad-impact or critical-service indicator."
    elif priority in {"P1", "SEV1", "CRITICAL"}:
        suggested = "Urgent Review"
        rationale = "The recorded priority is critical; validate business impact and escalation criteria."
    elif any(term in text for term in high_terms):
        suggested = "High Attention"
        rationale = "The incident text contains a service-degradation indicator."
    else:
        suggested = "Standard Triage"
        rationale = "No configured high-impact phrase was detected; review normal triage criteria."
    return {"triage_suggestion": suggested, "triage_rationale": rationale}


def recurring_incidents(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["normalized_summary"] = (
        work["summary"].fillna("").astype(str).str.lower()
        .str.replace(r"\b\d+\b", " ", regex=True)
        .str.replace(r"[^a-z0-9 ]", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True).str.strip()
    )
    grouped = (
        work.groupby(["service", "normalized_summary"], dropna=False)
        .agg(incident_count=("incident_id", "count"),
             latest_occurrence=("created_at", "max"),
             priorities=("priority", lambda x: ", ".join(sorted(set(map(str, x))))),
             incident_ids=("incident_id", lambda x: ", ".join(map(str, x))))
        .reset_index()
    )
    grouped = grouped[grouped["incident_count"] >= 2].sort_values(
        ["incident_count", "latest_occurrence"], ascending=[False, False]
    )
    return grouped


def build_mir(row: pd.Series, timeline: str, root_cause: str, corrective: str, preventive: str, owner: str) -> str:
    triage = classify_incident(row)
    created = str(row.get("created_at", "Not recorded"))
    duration = row.get("resolution_minutes", "Not recorded")
    try:
        duration_text = f"{float(duration):.0f} minutes"
    except (TypeError, ValueError):
        duration_text = str(duration)
    return f"""# Major Incident Report — {row.get('incident_id', 'Incident')}

## 1. Incident summary
- **Incident ID:** {row.get('incident_id', 'Not recorded')}
- **Service:** {row.get('service', 'Not recorded')}
- **Priority:** {row.get('priority', 'Not recorded')}
- **Status:** {row.get('status', 'Not recorded')}
- **Start / reported time:** {created}
- **Resolution duration:** {duration_text}
- **Triage suggestion:** {triage['triage_suggestion']}

## 2. Incident description
{row.get('summary', 'Not recorded')}

{row.get('description', 'No description supplied')}

## 3. Business impact
{row.get('business_impact', 'Not recorded')}

## 4. Timeline
{timeline.strip() or 'Add timestamped detection, escalation, investigation, mitigation, and recovery events.'}

## 5. Root cause
{root_cause.strip() or 'Root cause not yet confirmed. Record evidence and distinguish confirmed facts from hypotheses.'}

## 6. Corrective actions
{corrective.strip() or 'Document immediate actions taken to restore service.'}

## 7. Preventive actions
{preventive.strip() or 'Document long-term actions, owners, and target dates to reduce recurrence.'}

## 8. Action owner
{owner.strip() or 'Owner to be assigned'}

## 9. Review notes
This draft was generated from the selected incident record and user-provided notes. Validate all facts, timestamps, impact statements, and root-cause conclusions before sharing. The triage suggestion is rules-based and is not an automated declaration of a major incident.
"""


st.title("🛠️ ITSM Automation & RCA Assistant")
st.caption("Portfolio project • transparent incident triage • recurrence detection • MIR drafting")

with st.sidebar:
    st.header("Incident data")
    uploaded = st.file_uploader("Upload incident CSV", type=["csv"])
    st.caption("Use synthetic or approved, sanitized data only. Do not upload confidential production records.")
    st.divider()
    st.markdown("**Required columns**")
    st.code("incident_id, created_at, service, summary, description, priority, status, resolution_minutes, business_impact")

try:
    if uploaded is not None:
        raw_df = pd.read_csv(uploaded)
        source_label = f"Uploaded file: {uploaded.name}"
    else:
        raw_df = pd.read_csv(DEFAULT_DATA)
        source_label = "Bundled synthetic sample data"
except Exception as exc:
    st.error(f"Could not read the CSV: {exc}")
    st.stop()

df = normalize_columns(raw_df)
valid, message = validate_data(df)
if not valid:
    st.error(message)
    st.stop()

df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
df["resolution_minutes"] = pd.to_numeric(df["resolution_minutes"], errors="coerce")
df["priority"] = df["priority"].fillna("Unknown").astype(str).str.upper()
df["service"] = df["service"].fillna("Unknown").astype(str)
df["summary"] = df["summary"].fillna("").astype(str)
df["description"] = df["description"].fillna("").astype(str)
df["business_impact"] = df["business_impact"].fillna("").astype(str)
df["status"] = df["status"].fillna("Unknown").astype(str)

st.caption(f"Data source: {source_label} · {len(df):,} incident records")

with st.sidebar:
    priorities = sorted(df["priority"].unique().tolist())
    services = sorted(df["service"].unique().tolist())
    chosen_priorities = st.multiselect("Priority", priorities, default=priorities)
    chosen_services = st.multiselect("Service", services, default=services)

filtered = df[df["priority"].isin(chosen_priorities) & df["service"].isin(chosen_services)].copy()
if filtered.empty:
    st.warning("No incidents match the selected filters.")
    st.stop()

filtered["triage_suggestion"] = filtered.apply(lambda row: classify_incident(row)["triage_suggestion"], axis=1)
filtered["triage_rationale"] = filtered.apply(lambda row: classify_incident(row)["triage_rationale"], axis=1)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Incidents", f"{len(filtered):,}")
c2.metric("P1 incidents", int(filtered["priority"].isin(["P1", "SEV1", "CRITICAL"]).sum()))
c3.metric("Mean resolution", f"{filtered['resolution_minutes'].mean():.0f} min" if filtered["resolution_minutes"].notna().any() else "N/A")
c4.metric("Potential major incidents", int((filtered["triage_suggestion"] == "Potential Major Incident").sum()))

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Triage queue", "Recurring incidents", "MIR generator"])

with tab1:
    left, right = st.columns(2)
    with left:
        priority_counts = filtered["priority"].value_counts().rename_axis("Priority").reset_index(name="Count")
        st.plotly_chart(px.bar(priority_counts, x="Priority", y="Count", title="Incidents by priority"), use_container_width=True)
    with right:
        service_counts = filtered["service"].value_counts().rename_axis("Service").reset_index(name="Count")
        st.plotly_chart(px.bar(service_counts, x="Service", y="Count", title="Incidents by service"), use_container_width=True)
    trend = filtered.dropna(subset=["created_at"]).assign(Date=lambda x: x["created_at"].dt.date).groupby("Date").size().reset_index(name="Incidents")
    if not trend.empty:
        st.plotly_chart(px.line(trend, x="Date", y="Incidents", markers=True, title="Incident volume over time"), use_container_width=True)
    st.dataframe(filtered[["incident_id", "created_at", "service", "priority", "status", "summary", "triage_suggestion"]], use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Suggested triage — human review required")
    st.info("This is a transparent keyword/rule-based prototype, not a production severity engine. Always follow your organization's incident policy.")
    queue = filtered[["incident_id", "created_at", "service", "priority", "summary", "business_impact", "triage_suggestion", "triage_rationale"]].copy()
    st.dataframe(queue, use_container_width=True, hide_index=True)
    st.download_button("Download triage queue (CSV)", queue.to_csv(index=False).encode("utf-8"), "triage_queue.csv", "text/csv")

with tab3:
    repeats = recurring_incidents(filtered)
    st.subheader("Repeated incident patterns")
    if repeats.empty:
        st.success("No repeated summary patterns found within the current filters.")
    else:
        st.caption("Pattern matching normalizes case, punctuation, and digits. Similar wording may still be missed; matching is not proof of a shared root cause.")
        st.dataframe(repeats, use_container_width=True, hide_index=True)
        st.download_button("Download recurring patterns (CSV)", repeats.to_csv(index=False).encode("utf-8"), "recurring_patterns.csv", "text/csv")

with tab4:
    st.subheader("Generate a draft Major Incident Report")
    options = filtered["incident_id"].astype(str).tolist()
    selected_id = st.selectbox("Select incident", options)
    row = filtered[filtered["incident_id"].astype(str) == selected_id].iloc[0]
    st.write(f"**{row['service']} · {row['priority']} · {row['status']}**")
    st.write(f"**Summary:** {row['summary']}")
    st.write(f"**Business impact:** {row['business_impact']}")
    with st.form("mir_form"):
        timeline = st.text_area("Timeline", placeholder="09:10 — Alert detected\n09:15 — Incident declared\n09:35 — Mitigation applied\n10:00 — Service restored")
        root_cause = st.text_area("Root cause / current hypothesis", placeholder="State confirmed evidence separately from hypotheses.")
        corrective = st.text_area("Corrective actions taken")
        preventive = st.text_area("Preventive actions / follow-up")
        owner = st.text_input("Action owner")
        submitted = st.form_submit_button("Generate MIR draft")
    if submitted:
        mir = build_mir(row, timeline, root_cause, corrective, preventive, owner)
        st.markdown(mir)
        st.download_button("Download MIR as Markdown", mir.encode("utf-8"), f"MIR_{selected_id}.md", "text/markdown")

st.divider()
st.caption("Built with Streamlit, Pandas, and Plotly. RCA is decision support only; confirm root cause using evidence before publication.")

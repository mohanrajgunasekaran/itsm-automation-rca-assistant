import pandas as pd
from app import build_mir, classify_incident, recurring_incidents


def test_major_impact_phrase_suggests_major_incident():
    row = pd.Series({
        "summary": "Payment API complete outage",
        "description": "Production service unavailable",
        "business_impact": "Customer-wide payment disruption",
        "service": "Payments",
        "priority": "P1",
    })
    result = classify_incident(row)
    assert result["triage_suggestion"] == "Potential Major Incident"


def test_recurring_patterns_detect_repeated_summary():
    df = pd.DataFrame([
        {
            "incident_id": "A1",
            "service": "Network",
            "summary": "VPN connection drops",
            "created_at": "2026-09-01",
            "priority": "P2",
        },
        {
            "incident_id": "A2",
            "service": "Network",
            "summary": "VPN connection drops",
            "created_at": "2026-09-02",
            "priority": "P2",
        },
        {
            "incident_id": "B1",
            "service": "Database",
            "summary": "One-off error",
            "created_at": "2026-09-03",
            "priority": "P3",
        },
    ])

    result = recurring_incidents(df)

    assert len(result) == 1
    assert result.iloc[0]["incident_count"] == 2


def test_mir_contains_incident_and_root_cause():
    row = pd.Series({
        "incident_id": "INC1", "service": "Payments", "priority": "P1", "status": "Resolved",
        "created_at": "2026-09-01 08:00", "resolution_minutes": 60,
        "summary": "Payment outage", "description": "API unavailable",
        "business_impact": "Transactions delayed",
    })
    mir = build_mir(row, "08:00 detected", "Connection pool exhausted", "Restarted worker", "Add pool monitoring", "Ops")
    assert "INC1" in mir
    assert "Connection pool exhausted" in mir

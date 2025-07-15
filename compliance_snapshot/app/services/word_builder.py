from pathlib import Path
import sqlite3
import pandas as pd
from docx import Document
from .report_generator import (
    generate_hos_violations_summary,
    generate_summary_insights,
    generate_dot_risk_assessment,
)


def _load_data(wiz_id: str, table: str) -> pd.DataFrame:
    db_path = Path(f"/tmp/{wiz_id}/snapshot.db")
    con = sqlite3.connect(db_path)
    try:
        return pd.read_sql(f"SELECT * FROM {table}", con)
    finally:
        con.close()


def build_word(
    wiz_id: str,
    *,
    filters: dict | None = None,
    trend_end: str | None = None,
) -> Path:
    """Build a simple Word report using existing summary data."""
    tmpdir = Path(f"/tmp/{wiz_id}")
    out_path = tmpdir / "ComplianceSnapshot.docx"

    df = _load_data(wiz_id, "hos")
    if filters:
        for col, val in filters.items():
            if col in df.columns:
                df = df[df[col] == val]

    end_date = (
        pd.to_datetime(trend_end).date() if trend_end else pd.Timestamp.utcnow().date()
    )

    summary_data = generate_hos_violations_summary(df, end_date)
    insights = generate_summary_insights(summary_data)
    risk = generate_dot_risk_assessment(summary_data, None, None, None, None, None)

    doc = Document()
    doc.add_heading("DOT Compliance Snapshot", level=0)
    doc.add_heading("HOS Violations Summary", level=1)
    doc.add_paragraph(
        f"Total Violations: {summary_data['total_current']} ({summary_data['total_change']:+})"
    )
    for region, data in summary_data.get("by_region", {}).items():
        doc.add_paragraph(
            f"{region}: {data['current']} ({data['change']:+})",
            style="List Bullet",
        )
    doc.add_paragraph(insights)
    doc.add_heading("Overall DOT Risk Assessment", level=1)
    doc.add_paragraph(risk)
    doc.save(out_path)
    return out_path

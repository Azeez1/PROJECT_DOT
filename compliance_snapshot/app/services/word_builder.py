from pathlib import Path
import pandas as pd
from docx import Document

from .pdf_builder import load_data
from .report_generator import (
    generate_hos_violations_summary,
    generate_hos_trend_analysis,
    generate_summary_insights,
    generate_trend_insights,
)


def build_word(
    wiz_id: str, *, filters: dict | None = None, trend_end: str | None = None
) -> Path:
    """Generate a simplified Word version of the compliance snapshot."""
    tmpdir = Path(f"/tmp/{wiz_id}")
    out_path = tmpdir / "ComplianceSnapshot.docx"

    df = load_data(wiz_id, "hos")
    if filters:
        for col, val in filters.items():
            if col in df.columns:
                df = df[df[col] == val]

    end_date = (
        pd.to_datetime(trend_end).date() if trend_end else pd.Timestamp.utcnow().date()
    )

    summary = generate_hos_violations_summary(df, end_date)
    trend = generate_hos_trend_analysis(df, end_date)
    summary_insights = generate_summary_insights(summary)
    trend_insights = generate_trend_insights(trend)

    doc = Document()
    doc.add_heading("DOT COMPLIANCE SNAPSHOT", 0)

    doc.add_heading("HOS Violations Summary", level=1)
    p = doc.add_paragraph(
        f"Total Current: {summary['total_current']}\nTotal Previous: {summary['total_previous']}\nChange: {summary['total_change']}"
    )
    if summary.get("by_region"):
        doc.add_heading("By Region", level=2)
        table = doc.add_table(rows=1, cols=3)
        hdr = table.rows[0].cells
        hdr[0].text = "Region"
        hdr[1].text = "Current"
        hdr[2].text = "Change"
        for region, stats in summary["by_region"].items():
            row = table.add_row().cells
            row[0].text = region
            row[1].text = str(stats.get("current", ""))
            row[2].text = str(stats.get("change", ""))

    doc.add_heading("Summary Insights", level=2)
    doc.add_paragraph(summary_insights)

    doc.add_heading("4-Week Trend Insights", level=1)
    doc.add_paragraph(trend_insights)

    doc.save(out_path)
    return out_path

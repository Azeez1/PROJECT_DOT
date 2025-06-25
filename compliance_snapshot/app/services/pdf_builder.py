from __future__ import annotations

from pathlib import Path
import sqlite3
import pandas as pd
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    Spacer,
    Image,
)
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet

from .report_generator import (
    generate_hos_violations_summary,
    generate_hos_trend_analysis,
    generate_summary_insights,
    generate_trend_insights,
)

from .visualizations.chart_factory import make_stacked_bar, make_trend_line



def load_data(wiz_id: str, table: str) -> pd.DataFrame:
    db_path = Path(f"/tmp/{wiz_id}/snapshot.db")
    con = sqlite3.connect(db_path)
    try:
        return pd.read_sql(f'SELECT * FROM {table}', con)
    finally:
        con.close()


def build_pdf(
    wiz_id: str,
    *,
    filters: dict | None = None,
    trend_end: str | None = None,
    include_table: bool = False,
) -> Path:
    tmpdir = Path(f"/tmp/{wiz_id}")
    out_path = tmpdir / "ComplianceSnapshot.pdf"

    df = load_data(wiz_id, "hos")

    if filters:
        for col, val in filters.items():
            if col in df.columns:
                df = df[df[col] == val]

    # ----- table data -----
    if include_table:
        table_data = [df.columns.tolist()] + df.values.tolist()
    else:
        table_data = []

    end_date = pd.to_datetime(trend_end).date() if trend_end else None
    bar_path = make_stacked_bar(df, tmpdir / "bar.png")
    trend_path = make_trend_line(df, end_date, tmpdir / "trend.png")

    summary_data = generate_hos_violations_summary(df, end_date or pd.Timestamp.utcnow().date())
    trend_data = generate_hos_trend_analysis(df, end_date or pd.Timestamp.utcnow().date())

    print(f"DEBUG: Calling generate_summary_insights...")
    summary_insights = generate_summary_insights(summary_data)
    print(f"DEBUG: Generated insights: {summary_insights}")

    trend_insights = generate_trend_insights(trend_data)


    # ----- build the PDF -----
    styles = getSampleStyleSheet()
    # Use ``SimpleDocTemplate`` so we don't need to manage custom page
    # templates for this straightforward document.
    doc = SimpleDocTemplate(str(out_path), pagesize=LETTER)
    story = [Paragraph("HOS Violations Snapshot", styles["Heading1"])]

    if include_table and table_data:
        story.extend([Table(table_data, repeatRows=1, hAlign="LEFT"), Spacer(1, 12)])

    story.extend([
        Paragraph("HOS Violations Summary", styles["Heading2"]),
        Paragraph(
            f"Total Violations: {summary_data['total_current']} ({summary_data['total_change']:+})",
            styles["Normal"],
        ),
    ])

    for region, data in summary_data.get("by_region", {}).items():
        story.append(
            Paragraph(
                f"{region}: {data['current']} ({data['change']:+})",
                styles["Normal"],
            )
        )

    story.append(Paragraph("Top Violation Types:", styles["Normal"]))
    for vt, data in summary_data.get("by_type", {}).items():
        story.append(
            Paragraph(
                f"{vt}: {data['current']} ({data['change']:+})",
                styles["Normal"],
            )
        )

    story.append(Image(str(bar_path), width=450, height=225))
    story.append(Spacer(1, 12))
    story.append(Paragraph(summary_insights, styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("HOS Violation Trend (4 weeks)", styles["Heading2"]))
    story.append(Image(str(trend_path), width=450, height=225))
    story.append(Spacer(1, 12))
    story.append(Paragraph(trend_insights, styles["Normal"]))

    doc.build(story)
    return out_path

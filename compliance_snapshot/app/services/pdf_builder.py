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


    # ----- build the PDF -----
    styles = getSampleStyleSheet()
    # Use ``SimpleDocTemplate`` so we don't need to manage custom page
    # templates for this straightforward document.
    doc = SimpleDocTemplate(str(out_path), pagesize=LETTER)
    story = [Paragraph("HOS Violations Snapshot", styles["Heading1"])]

    if include_table and table_data:
        story.extend([Table(table_data, repeatRows=1, hAlign="LEFT"), Spacer(1, 12)])

    story.extend([
        Image(str(bar_path), width=450, height=225),
        Spacer(1, 12),
        Image(str(trend_path), width=450, height=225),
    ])

    doc.build(story)
    return out_path

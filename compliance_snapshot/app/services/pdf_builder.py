from __future__ import annotations

from pathlib import Path
import sqlite3
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer, Image
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


def build_pdf(wiz_id: str) -> Path:
    tmpdir = Path(f"/tmp/{wiz_id}")
    out_path = tmpdir / "ComplianceSnapshot.pdf"

    df = load_data(wiz_id, "hos")

    # ----- 1️⃣ convert current table -----
    table_data = [df.columns.tolist()] + df.values.tolist()

    # ----- charts -----
    bar_path = make_stacked_bar(df, tmpdir / "bar.png")
    trend_path = make_trend_line(df, tmpdir / "trend.png")

    # ----- build the PDF -----
    styles = getSampleStyleSheet()
    # Use ``SimpleDocTemplate`` so we don't need to manage custom page
    # templates for this straightforward document.
    doc = SimpleDocTemplate(str(out_path), pagesize=LETTER)
    story = [
        Paragraph("HOS Violations Snapshot", styles["Heading1"]),
        Table(table_data, repeatRows=1, hAlign="LEFT"),
        Spacer(1, 12),
        Image(str(bar_path), width=480, height=260),
        Spacer(1, 12),
        Image(str(trend_path), width=480, height=260),
    ]
    doc.build(story)
    return out_path

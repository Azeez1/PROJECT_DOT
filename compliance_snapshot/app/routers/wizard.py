from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi import Form
from fastapi.templating import Jinja2Templates
import sqlite3
from pathlib import Path
import pandas as pd
<<<<<< codex/add-manual-trend-end-date-control
from ..services.visualizations.chart_factory import make_chart, make_trend_line
=======
from ..services.visualizations.chart_factory import (
    make_stacked_bar,
    make_trend_line,
)
>>>>>> main
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

router = APIRouter()
templates = Jinja2Templates(directory="compliance_snapshot/app/templates")
_db = lambda t: Path(f"/tmp/{t}/snapshot.db")

@router.get("/wizard/{ticket}", response_class=HTMLResponse)
async def wizard(request: Request, ticket: str):
    if not _db(ticket).exists():
        raise HTTPException(404, "ticket not found")
    return templates.TemplateResponse("wizard.html",
                                      {"request": request, "ticket": ticket})

@router.get("/api/{ticket}/tables")
async def list_tables(ticket: str):
    con = sqlite3.connect(_db(ticket))
    cur = con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall()]

@router.get("/api/{ticket}/query")
async def query_table(ticket: str, table: str, limit: int | None = None):
    """Return rows from the requested table.

    Args:
        ticket: Upload ticket identifier.
        table: Table name within the SQLite DB.
        limit: Optional row limit. If ``None`` all rows are returned.
    """
    con = sqlite3.connect(_db(ticket))
    cols = [c[1] for c in con.execute(f'PRAGMA table_info("{table}")')]
    query = f'SELECT * FROM "{table}"'
    if limit is not None:
        query += f' LIMIT {int(limit)}'
    rows = con.execute(query).fetchall()
    return JSONResponse({"columns": cols, "rows": rows})


@router.post("/finalize/{ticket}")
async def finalize(ticket: str,
                   chart_hos: str = Form("on"),
                   chart_type: str = Form("bar"),
                   trend_end: str | None = Form(None)):
    db_file = _db(ticket)
    if not db_file.exists():
        raise HTTPException(404, "ticket not found")

    # Load full HOS DataFrame
    con = sqlite3.connect(db_file)
    df = pd.read_sql('SELECT * FROM hos', con)
<<<<<< codex/add-manual-trend-end-date-control
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    # ----- 4-week slice based on trend_end (defaults to latest) -----
    df2 = df.copy()
    if 'WEEK OF...' in df2.columns:
        df2['week'] = pd.to_datetime(df2['WEEK OF...'])
    elif 'week_of...' in df2.columns:
        df2['week'] = pd.to_datetime(df2['week_of...'])
    else:
        df2['week'] = pd.NaT
    end_dt = pd.to_datetime(trend_end) if trend_end else df2['week'].max()
    start_dt = end_dt - pd.Timedelta(weeks=3)
    df4 = df2[(df2['week'] >= start_dt) & (df2['week'] <= end_dt)]
    wo2 = df4.groupby('week').size().sort_index()

    # 2) make chart if requested
    charts_dir = Path(f"/tmp/{ticket}/charts"); charts_dir.mkdir(exist_ok=True)
    chart_path = charts_dir / "hos.png"
    trend_path = charts_dir / "trend.png"
    if chart_hos == "on":
        make_chart(
            df,
            chart_type,
            chart_path,
            title="HOS Violations by Type",
        )
        make_trend_line(df4, trend_path)

    # 3) build simple PDF
    pdf_path = Path(f"/tmp/{ticket}/ComplianceSnapshot.pdf")
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, 750, "Compliance Snapshot \u2013 HOS")
    c.setFont("Helvetica", 11)
    c.drawString(40, 730, f"Total violations: {len(df)}")
    if chart_path.exists():
        c.drawImage(str(chart_path), 40, 460, width=520, height=250)
    if trend_path.exists():
        c.drawImage(str(trend_path), 40, 200, width=520, height=220)
    c.showPage(); c.save()
=======

    # Prepare chart files
    charts_dir = Path(f"/tmp/{ticket}/charts")
    charts_dir.mkdir(exist_ok=True)
    stacked_path = charts_dir / "hos_stacked.png"
    trend_path = charts_dir / "hos_trend.png"

    # Generate charts
    make_stacked_bar(df, stacked_path)
    make_trend_line(df, trend_path)

    # Build PDF: Page 1 with both charts
    pdf_path = Path(f"/tmp/{ticket}/ComplianceSnapshot.pdf")
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, 770, "Compliance Snapshot \u2013 HOS")
    c.setFont("Helvetica", 10)
    total = len(df)
    c.drawString(40, 755, f"Total Violations: {total}")
    c.drawImage(str(stacked_path), 40, 450, width=260, height=180)
    c.drawImage(str(trend_path), 300, 450, width=260, height=180)
    c.showPage()

    # Page 2: narrative summary
    # Compute region breakdown
    region_counts = df.groupby('Tags').size().to_dict()
    gl = region_counts.get('Great Lakes', 0)
    ov = region_counts.get('Ohio Valley', 0)
    se = region_counts.get('Southeast', 0)

    # Compute week-over-week trend
    last_two = df.copy()
    last_two['week'] = pd.to_datetime(last_two['WEEK OF...'])
    wo2 = last_two.groupby('week').size().sort_index()
    prev, curr = wo2.iloc[-2], wo2.iloc[-1]
    trend = (
        "increased" if curr > prev else "decreased" if curr < prev else "remained flat"
    )

    narrative = (
        f"Total violations: {total} (+{total - prev}).\n"
        f"Violations by Region:\n"
        f"  \u2022 Great Lakes: {gl}\n"
        f"  \u2022 Ohio Valley: {ov}\n"
        f"  \u2022 Southeast: {se}\n"
        f"Week-over-Week Trend: {trend} "
        f"({prev} \u2192 {curr})."
    )

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, 750, "HOS Violations Summary")
    c.setFont("Helvetica", 10)
    text = c.beginText(40, 730)
    for line in narrative.split('\n'):
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
>>>>>> main

    # Return PDF as attachment
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition":
                 "attachment; filename=ComplianceSnapshot.pdf"},
    )

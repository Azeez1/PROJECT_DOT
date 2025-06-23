from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi import Form
from fastapi.templating import Jinja2Templates
import sqlite3
from pathlib import Path
import pandas as pd
from ..services.visualizations.chart_factory import (
    make_stacked_bar,
    make_trend_line,
)
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

    con = sqlite3.connect(db_file)
    df = pd.read_sql("SELECT * FROM hos", con)

    norm = {c.lower().replace(" ", "_").replace(".", ""): c for c in df.columns}
    week_col = next((c for k, c in norm.items() if k.startswith("week")), None)
    if not week_col:
        raise HTTPException(500, "week column not found")

    df["week"] = pd.to_datetime(df[week_col])
    end_dt = pd.to_datetime(trend_end) if trend_end else df["week"].max()
    start_dt = end_dt - pd.Timedelta(weeks=3)
    window_df = df[(df["week"] >= start_dt) & (df["week"] <= end_dt)]

    charts_dir = Path(f"/tmp/{ticket}/charts")
    charts_dir.mkdir(exist_ok=True)
    stacked_path = charts_dir / "hos_stacked.png"
    trend_path = charts_dir / "hos_trend.png"

    make_stacked_bar(df, stacked_path)
    make_trend_line(window_df, trend_path)

    pdf_path = Path(f"/tmp/{ticket}/ComplianceSnapshot.pdf")
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, 770, "Compliance Snapshot \u2013 HOS")
    c.setFont("Helvetica", 10)
    total = len(df)
    c.drawString(40, 755, f"Total Violations: {total}")
    if stacked_path.exists():
        c.drawImage(str(stacked_path), 40, 450, width=260, height=180)
    if trend_path.exists():
        c.drawImage(str(trend_path), 300, 450, width=260, height=180)
    c.showPage()

    region_counts = df.groupby("Tags").size().to_dict() if "Tags" in df.columns else {}
    gl = region_counts.get("Great Lakes", 0)
    ov = region_counts.get("Ohio Valley", 0)
    se = region_counts.get("Southeast", 0)

    weekly = df.groupby("week").size().sort_index()
    if len(weekly) >= 2:
        prev, curr = weekly.iloc[-2], weekly.iloc[-1]
    elif len(weekly) == 1:
        prev = curr = weekly.iloc[0]
    else:
        prev = curr = 0

    if curr > prev:
        trend = "increased"
    elif curr < prev:
        trend = "decreased"
    else:
        trend = "remained flat"

    narrative = (
        f"Total violations: {total}.\n"
        f"Violations by Region:\n"
        f"  \u2022 Great Lakes: {gl}\n"
        f"  \u2022 Ohio Valley: {ov}\n"
        f"  \u2022 Southeast: {se}\n"
        f"Week-over-Week Trend: {trend} ({prev} \u2192 {curr})."
    )

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, 750, "HOS Violations Summary")
    c.setFont("Helvetica", 10)
    text = c.beginText(40, 730)
    for line in narrative.split("\n"):
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=ComplianceSnapshot.pdf"},
    )

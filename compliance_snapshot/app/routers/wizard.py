from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from pathlib import Path
import pandas as pd
from ..services.visualizations.chart_factory import make_chart
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
                   chart_hos: str = "on",
                   chart_type: str = "bar"):
    db_file = _db(ticket)
    if not db_file.exists():
        raise HTTPException(404, "ticket not found")

    # 1) query full (or later: filtered) DataFrame
    con = sqlite3.connect(db_file)
    df = pd.read_sql('SELECT * FROM hos', con)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    # 2) make chart if requested
    charts_dir = Path(f"/tmp/{ticket}/charts"); charts_dir.mkdir(exist_ok=True)
    chart_path = charts_dir / "hos.png"
    if chart_hos == "on":
        make_chart(
            df,
            chart_type,
            chart_path,
            title="HOS Violations by Type",
        )

    # 3) build simple PDF
    pdf_path = Path(f"/tmp/{ticket}/ComplianceSnapshot.pdf")
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, 750, "Compliance Snapshot \u2013 HOS")
    c.setFont("Helvetica", 11)
    c.drawString(40, 730, f"Total violations: {len(df)}")
    if chart_path.exists():
        c.drawImage(str(chart_path), 40, 460, width=520, height=250)
    c.showPage(); c.save()

    from fastapi.responses import FileResponse
    # use FileResponse's filename parameter to set the Content-Disposition header
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename="ComplianceSnapshot.pdf",
    )

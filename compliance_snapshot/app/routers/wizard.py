from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    FileResponse,
)
from fastapi.templating import Jinja2Templates
import sqlite3
import json
from pathlib import Path
from ..services.pdf_builder import build_pdf

router = APIRouter()
templates = Jinja2Templates(directory="compliance_snapshot/app/templates")
_db = lambda t: Path(f"/tmp/{t}/snapshot.db")
_err = lambda t: Path(f"/tmp/{t}/errors.json")

@router.get("/wizard/{ticket}", response_class=HTMLResponse)
async def wizard(request: Request, ticket: str):
    if not _db(ticket).exists():
        raise HTTPException(404, "ticket not found")
    return templates.TemplateResponse("wizard.html",
                                      {"request": request, "ticket": ticket})


@router.get("/api/{ticket}/errors")
async def list_errors(ticket: str):
    path = _err(ticket)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except Exception:
        data = []
    return data

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


@router.post("/finalize/{wiz_id}")
async def finalize(wiz_id: str, request: Request):
    """Generate and immediately return the PDF snapshot."""

    db_file = _db(wiz_id)
    if not db_file.exists():
        raise HTTPException(404, "ticket not found")

    payload = await request.json()
    filters = payload.get("filters") or {}
    trend_end = payload.get("trend_end")

    pdf_path = build_pdf(wiz_id, filters=filters, trend_end=trend_end)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"DOT_Compliance_{wiz_id[:8]}.pdf",
    )

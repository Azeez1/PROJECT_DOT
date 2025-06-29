from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
)
from fastapi.templating import Jinja2Templates
import sqlite3
import json
from pathlib import Path
from ..services.pdf_builder import build_pdf
from ..core.utils import file_response

router = APIRouter()
templates = Jinja2Templates(directory="compliance_snapshot/app/templates")


def _db(ticket: str) -> Path:
    return Path(f"/tmp/{ticket}/snapshot.db")


def _summary(ticket: str) -> Path:
    return Path(f"/tmp/{ticket}/summary.json")


def _err(ticket: str) -> Path:
    return Path(f"/tmp/{ticket}/errors.json")
@router.get("/wizard/{ticket}", response_class=HTMLResponse)
async def wizard(request: Request, ticket: str):
    if not _db(ticket).exists():
        raise HTTPException(404, "ticket not found")
    summary = {}
    sp = _summary(ticket)
    if sp.exists():
        try:
            summary = json.loads(sp.read_text())
        except Exception:
            summary = {}
    return templates.TemplateResponse(
        "wizard.html",
        {"request": request, "ticket": ticket, "summary": summary},
    )


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
    try:
        con = sqlite3.connect(_db(ticket))
        cur = con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [r[0] for r in cur.fetchall()]
    except Exception as exc:
        raise HTTPException(500, f"database error: {exc}")

@router.get("/api/{ticket}/query")
async def query_table(ticket: str, table: str, limit: int | None = None):
    """Return rows from the requested table.

    Args:
        ticket: Upload ticket identifier.
        table: Table name within the SQLite DB.
        limit: Optional row limit. If ``None`` all rows are returned.
    """
    try:
        con = sqlite3.connect(_db(ticket))
        cols = [c[1] for c in con.execute(f'PRAGMA table_info("{table}")')]
        query = f'SELECT * FROM "{table}"'
        if limit is not None:
            query += f' LIMIT {int(limit)}'
        rows = con.execute(query).fetchall()
        return JSONResponse({"columns": cols, "rows": rows})
    except Exception as exc:
        raise HTTPException(500, f"query failed: {exc}")


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
    return file_response(
        pdf_path,
        filename=f"DOT_Compliance_{wiz_id[:8]}.pdf",
        media_type="application/pdf",
    )

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Form
from fastapi.templating import Jinja2Templates
import sqlite3
from pathlib import Path
import pandas as pd
from ..services.visualizations.chart_factory import make_chart, make_trend_line
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
                   chart_type: str = Form("bar")):
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

    charts_dir = Path(f"/tmp/{ticket}/charts")
    charts_dir.mkdir(exist_ok=True)
    chart_path = charts_dir / "hos_chart.png"

    if chart_type == "line":
        make_trend_line(df, chart_path)
    else:
        make_chart(df, chart_type, chart_path, title="Violations by Type")

    pdf_path = Path(f"/tmp/{ticket}/ComplianceSnapshot.pdf")
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, 770, "Compliance Snapshot \u2013 HOS")
    c.setFont("Helvetica", 10)
    total = len(df)
    c.drawString(40, 755, f"Total Violations: {total}")
    if chart_path.exists():
        c.drawImage(str(chart_path), 40, 450, width=520, height=250)
    c.showPage()

    region_col = norm.get("tags") or norm.get("region")
    if region_col:
        region_counts = df.groupby(region_col).size().to_dict()
    else:
        region_counts = {}
    gl = region_counts.get("Great Lakes", 0)
    ov = region_counts.get("Ohio Valley", 0)
    se = region_counts.get("Southeast", 0)

    weekly = df.groupby("week").size().sort_index()
    if len(weekly) >= 2:
        prev_total, curr_total = weekly.iloc[-2], weekly.iloc[-1]
        prev_week, curr_week = weekly.index[-2], weekly.index[-1]
    elif len(weekly) == 1:
        prev_total = curr_total = weekly.iloc[0]
        prev_week = curr_week = weekly.index[0]
    else:
        prev_total = curr_total = 0
        prev_week = curr_week = None

    if curr_total > prev_total:
        trend = "increased"
    elif curr_total < prev_total:
        trend = "decreased"
    else:
        trend = "remained flat"

    # Determine regional weekly counts if week information is available
    region_weekly = None
    if curr_week is not None and region_col:
        region_weekly = (
            df.pivot_table(index=region_col, columns="week", aggfunc="size", fill_value=0)
        )

    def _region_line(region: str) -> str:
        current = region_weekly.loc[region, curr_week] if region_weekly is not None and region in region_weekly.index else region_counts.get(region, 0)
        if region_weekly is not None and prev_week in region_weekly.columns:
            prev_val = region_weekly.loc[region, prev_week]
            diff = current - prev_val
            diff_str = f"({diff:+d})"
        else:
            diff_str = ""
        return f"  \u2022 {region}: {current} {diff_str}".rstrip()

    # Top violation types and week-over-week diffs
    vt_col = norm.get("violation_type")
    top_lines: list[str] = []
    if vt_col and curr_week is not None:
        type_week = df.pivot_table(index=vt_col, columns="week", aggfunc="size", fill_value=0)
        if curr_week in type_week.columns:
            sorted_types = type_week[curr_week].sort_values(ascending=False)
            for v_type, curr_val in sorted_types.head(5).items():
                if prev_week in type_week.columns:
                    prev_val = int(type_week.at[v_type, prev_week])
                    diff = curr_val - prev_val
                    diff_str = f"({diff:+d})"
                else:
                    diff_str = ""
                top_lines.append(f"  \u2022 {v_type}: {int(curr_val)} {diff_str}".rstrip())

    total_diff = curr_total - prev_total
    total_line = f"Total Violations: {curr_total} ({total_diff:+d})"

    narrative_lines = [
        total_line,
        "\u2022 Violations by Region:",
        _region_line("Great Lakes"),
        _region_line("Ohio Valley"),
        _region_line("Southeast"),
        "\u2022 HOS Violations Week-over-Week Comparison:",
        f"  \u2022 Trend: {trend}",
        f"    (Previous Week: {prev_total} \u2192 This Week: {curr_total})",
    ]

    if top_lines:
        narrative_lines.append("\u2022 Top Violation Types:")
        narrative_lines.extend(top_lines)

    narrative = "\n".join(narrative_lines)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, 750, "HOS Violations Summary")
    text = c.beginText(40, 730)
    for line in narrative.split("\n"):
        if line.strip() in {
            "\u2022 Violations by Region:",
            "\u2022 HOS Violations Week-over-Week Comparison:",
            "\u2022 Top Violation Types:",
        }:
            text.setFont("Helvetica-Bold", 10)
        else:
            text.setFont("Helvetica", 10)
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()

    # PDF is now ready for download via /download
    return JSONResponse({"status": "ok"})

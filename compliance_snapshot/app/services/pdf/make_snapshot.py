from __future__ import annotations

from pathlib import Path
import pandas as pd
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle


def load_table(path: str | Path) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame."""
    p = Path(path)
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    return pd.read_excel(p, engine="openpyxl")


def make_snapshot(state: dict, *, include_table: bool = False) -> Path:
    """Create the final PDF snapshot with optional table and charts."""
    df = load_table(state["csv_path"])
    chart_paths: list[str | Path] = state.get("chart_paths", [])
    out = Path(state.get("pdf_path", "snapshot.pdf"))

    c = rl_canvas.Canvas(str(out), pagesize=LETTER)

    if include_table:
        # ---------- COMPACT SUMMARY TABLE ----------
        summary = (
            df.pivot_table(
                index="Tags",
                columns="Violation Type",
                aggfunc="size",
                fill_value=0,
            )
            .reset_index()
        )

        header = ["Region"] + summary.columns.tolist()[1:]
        rows = summary.values.tolist()
        table = Table([header] + rows, repeatRows=1)

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 7),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]
            )
        )

        w, h = table.wrap(540, 400)
        table.drawOn(c, 36, 720 - h)
        y = 720 - h - 20
    else:
        y = 720

    # ---------- chart images (unchanged) ----------
    for img in chart_paths:
        try:
            c.drawImage(str(img), 36, y - 240, width=540, height=240)
            y -= 260
        except Exception:
            continue

    c.showPage()
    c.save()
    return out

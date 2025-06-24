from __future__ import annotations

import io
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import datetime, date
from typing import Optional

import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet

from .visualizations.chart_factory import make_stacked_bar, make_trend_line


def build_pdf(hos_df: pd.DataFrame, end_date: Optional[date] = None) -> bytes:
    """Return a PDF report containing violation charts for ``hos_df``."""

    if end_date is None:
        end_date = datetime.utcnow().date()

    with NamedTemporaryFile(suffix=".png", delete=False) as bar_tmp, \
         NamedTemporaryFile(suffix=".png", delete=False) as trend_tmp:
        bar_path = Path(bar_tmp.name)
        trend_path = Path(trend_tmp.name)
        make_stacked_bar(hos_df, bar_path)
        # ``make_trend_line`` in repository does not require ``end_date``
        try:
            make_trend_line(hos_df, trend_path)
        except TypeError:
            # If newer signature requires end_date
            make_trend_line(hos_df, end_date, trend_path)  # type: ignore

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    flowables: list = []

    flowables.append(Paragraph("HOS Violations", styles["Heading2"]))
    flowables.append(Image(bar_path.as_posix(), width=450, height=225))
    flowables.append(Spacer(1, 12))

    flowables.append(Paragraph("HOS 4-Week Trend Analysis", styles["Heading2"]))
    flowables.append(Image(trend_path.as_posix(), width=450, height=225))
    flowables.append(Spacer(1, 12))

    doc.build(flowables)
    buffer.seek(0)
    return buffer.getvalue()

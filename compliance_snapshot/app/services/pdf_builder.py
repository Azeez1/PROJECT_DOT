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
    PageBreak,
)
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from .report_generator import (
    generate_hos_violations_summary,
    generate_hos_trend_analysis,
    generate_summary_insights,
    generate_trend_insights,
)

from .visualizations.chart_factory import make_stacked_bar, make_trend_line

import re


def convert_html_to_reportlab(text: str) -> str:
    """Convert HTML span tags to ReportLab font tags."""
    if not text:
        return ""
    return re.sub(r'<span style="color:\s*red;">([^<]+)</span>', r'<font color="red">\1</font>', text)



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

    summary_data = generate_hos_violations_summary(df, end_date or pd.Timestamp.utcnow().date())
    trend_data = generate_hos_trend_analysis(df, end_date or pd.Timestamp.utcnow().date())

    print(f"DEBUG: Calling generate_summary_insights...")
    summary_insights = generate_summary_insights(summary_data)
    print(f"DEBUG: Generated insights: {summary_insights}")

    trend_insights = generate_trend_insights(trend_data)

    # Convert potential HTML to ReportLab-safe tags
    summary_insights = convert_html_to_reportlab(summary_insights)
    trend_insights = convert_html_to_reportlab(trend_insights)


    # ----- build the PDF -----
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out_path), pagesize=LETTER)

    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#000000'),
        spaceAfter=20,
        alignment=1  # Center alignment
    )

    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#000000'),
        spaceAfter=12,
        spaceBefore=20
    )

    normal_bold = ParagraphStyle(
        'NormalBold',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )

    story = []

    # Add main title at the very top
    story.append(Paragraph("COMPLIANCE REPORT", title_style))
    story.append(Spacer(1, 20))

    # Add both charts at the top of the page
    story.append(Image(str(bar_path), width=350, height=230))
    story.append(Spacer(1, 12))
    story.append(Image(str(trend_path), width=350, height=230))

    # Force page break to start Page 2
    story.append(PageBreak())

    # Add main title on Page 2
    story.append(Paragraph("DOT COMPLIANCE SNAPSHOT", title_style))

    # HOS Violations Summary section
    story.append(Paragraph("<b>HOS Violations Summary:</b>", section_title_style))

    # Create a two-column layout for the summary
    summary_items = []

    # Left column items
    left_items = []
    left_items.append(Paragraph(f"• <b>Total Violations:</b> {summary_data['total_current']} ({summary_data['total_change']:+})", styles['Normal']))

    left_items.append(Paragraph("• <b>Violations by Region:</b>", styles['Normal']))
    for region, data in summary_data.get("by_region", {}).items():
        sign = "+" if data['change'] >= 0 else ""
        left_items.append(Paragraph(f"   ○ {region}: {data['current']} ({sign}{data['change']})", styles['Normal']))

    left_items.append(Paragraph("• <b>HOS Violations Week-over-Week Comparison:</b>", styles['Normal']))
    left_items.append(Paragraph(f"   ○ Trend: {'increased' if summary_data['total_change'] > 0 else 'decreased' if summary_data['total_change'] < 0 else 'stable'}", styles['Normal']))
    left_items.append(Paragraph(f"   (Previous Week: {summary_data['total_previous']} → This Week: {summary_data['total_current']})", styles['Normal']))

    # Right column items
    right_items = []
    right_items.append(Paragraph("• <b>Top Violation Types:</b>", styles['Normal']))
    for vt, data in list(summary_data.get("by_type", {}).items())[:5]:  # Top 5 violation types
        sign = "+" if data['change'] >= 0 else ""
        right_items.append(Paragraph(f"   ○ {vt}: {data['current']} ({sign}{data['change']})", styles['Normal']))

    # Create table for two-column layout
    from reportlab.platypus import TableStyle as RLTableStyle
    summary_table_data = [[left_items, right_items]]
    summary_table = Table(summary_table_data, colWidths=[doc.width * 0.5, doc.width * 0.5])
    summary_table.setStyle(RLTableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # Summary Insights section
    story.append(Paragraph("<b>Insights:</b>", normal_bold))
    story.append(Paragraph(summary_insights, styles['Normal']))
    story.append(Spacer(1, 30))

    # HOS Violation Trend section
    story.append(Paragraph("<b>HOS Violation Trend (4 weeks)</b>", section_title_style))
    story.append(Spacer(1, 12))

    # Trend Insights
    story.append(Paragraph("<b>Insights:</b>", normal_bold))
    story.append(Paragraph(trend_insights, styles['Normal']))

    doc.build(story)
    return out_path

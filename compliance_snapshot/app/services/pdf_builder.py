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
    generate_safety_inbox_summary,  # Add this
    generate_safety_inbox_insights,  # Add this
    generate_pc_usage_summary,
    generate_pc_usage_insights,
    generate_unassigned_driving_summary,
    generate_unassigned_driving_insights,
)

from .visualizations.chart_factory import (
    make_stacked_bar,
    make_trend_line,
    make_unassigned_bar_chart,
)

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

    # Add Safety Inbox Events Analysis if the data exists
    try:
        safety_inbox_df = load_data(wiz_id, "safety_inbox")
        if not safety_inbox_df.empty:
            # Safety Inbox Events Analysis section
            story.append(Spacer(1, 30))
            story.append(Paragraph("<b>Safety Inbox Events Analysis</b>", section_title_style))

            # Generate summary data
            safety_inbox_data = generate_safety_inbox_summary(
                safety_inbox_df, end_date or pd.Timestamp.utcnow().date()
            )

            # Create two-column layout
            left_items = []
            right_items = []

            # Left column - main statistics
            left_items.append(Paragraph(f"• <b>Total Safety Events:</b> {safety_inbox_data['total_current']} ({safety_inbox_data['total_change']:+})", styles['Normal']))
            left_items.append(Paragraph(f"• <b>Dismissed:</b> {safety_inbox_data['dismissed_count']}", styles['Normal']))
            left_items.append(Paragraph("• <b>Breakdown by Region:</b>", styles['Normal']))
            for region, count in safety_inbox_data.get("by_region", {}).items():
                left_items.append(Paragraph(f"   ○ {region}: {count}", styles['Normal']))

            # Right column - event breakdown
            right_items.append(Paragraph("<b>Event Breakdown:</b>", styles['Normal']))
            for event, count in safety_inbox_data.get("event_breakdown", {}).items():
                right_items.append(Paragraph(f"• {event}: {count}", styles['Normal']))

            # Create the two-column table
            from reportlab.platypus import TableStyle as RLTableStyle
            safety_table_data = [[left_items, right_items]]
            safety_table = Table(safety_table_data, colWidths=[doc.width * 0.5, doc.width * 0.5])
            safety_table.setStyle(RLTableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(safety_table)
            story.append(Spacer(1, 20))

            # Add insights
            story.append(Paragraph("<b>Insights:</b>", normal_bold))
            safety_insights = generate_safety_inbox_insights(safety_inbox_data)
            safety_insights = convert_html_to_reportlab(safety_insights)
            story.append(Paragraph(safety_insights, styles['Normal']))

    except Exception as e:
        print(f"Error adding Safety Inbox analysis: {e}")

    # Personal Conveyance (PC) Usage section
    try:
        pc_df = load_data(wiz_id, "personnel_conveyance")
        if not pc_df.empty:
            story.append(Spacer(1, 30))
            story.append(Paragraph("Personal Conveyance (PC) Usage", section_title_style))

            pc_data = generate_pc_usage_summary(pc_df, end_date or pd.Timestamp.utcnow().date())

            story.append(Paragraph("• Per Driver PC Goal: Max 2 hours/day or 14 hours/week", styles['Normal']))
            story.append(Paragraph(f"• Total PC Time: {pc_data['total_pc_time']:.2f} hours", styles['Normal']))
            story.append(Paragraph("• Top PC Users:", styles['Normal']))

            table_rows = [["DRIVERS", "Sum of Personal Conveyance (Duration)"]]
            for item in pc_data.get("drivers_list", []):
                td = pd.to_timedelta(item['hours'], unit='h')
                dur = str(td).split(" ")[-1].split(".")[0]
                table_rows.append([item['driver'], dur])
            total_td = pd.to_timedelta(pc_data['total_pc_time'], unit='h')
            total_dur = str(total_td).split(" ")[-1].split(".")[0]
            table_rows.append(["Grand Total", total_dur])

            from reportlab.platypus import TableStyle as RLTableStyle
            pc_table = Table(table_rows, colWidths=[doc.width * 0.5, doc.width * 0.5])
            pc_table.setStyle(RLTableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#B8CCE4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            story.append(pc_table)
            story.append(Spacer(1, 12))
            story.append(Paragraph(
                "NOTE: All drivers on this report were noted as driving 3+ hours of PC for at least 1 day during the review period",
                styles['Normal'],
            ))
    except Exception as e:
        print(f"Error loading Personal Conveyance data: {e}")

    # Unassigned Driving Segments section
    try:
        unassigned_df = load_data(wiz_id, "unassigned_hos")
        if not unassigned_df.empty:
            story.append(Spacer(1, 30))
            story.append(Paragraph("Unassigned Driving Segments", section_title_style))

            unassigned_data = generate_unassigned_driving_summary(
                unassigned_df, end_date or pd.Timestamp.utcnow().date()
            )

            chart_path = make_unassigned_bar_chart(
                unassigned_data.get("chart", {}), tmpdir / "unassigned_bar.png"
            )
            story.append(Image(str(chart_path), width=350, height=230))
            story.append(Spacer(1, 12))

            story.append(Paragraph("<b>Insights:</b>", normal_bold))
            unassigned_insights = generate_unassigned_driving_insights(unassigned_data)
            unassigned_insights = convert_html_to_reportlab(unassigned_insights)
            story.append(Paragraph(unassigned_insights, styles['Normal']))
    except Exception as e:
        print(f"Error loading Unassigned HOS data: {e}")

    doc.build(story)
    return out_path

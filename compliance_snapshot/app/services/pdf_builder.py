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
    generate_unassigned_driving_summary,  # Added missing import
    generate_unassigned_driving_insights,
    generate_unassigned_segment_details,
)

from .visualizations.chart_factory import (
    make_stacked_bar,
    make_trend_line,
    make_pc_usage_bar_chart,
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

            story.append(Paragraph("• <b>Per Driver PC Goal:</b> Max 2 hours/day or 14 hours/week", styles['Normal']))
            story.append(Paragraph(f"• <b>Total PC Time:</b> {pc_data['total_pc_time']} hours", styles['Normal']))
            story.append(Paragraph("• <b>Top PC Users:</b>", styles['Normal']))

            table_data = [
                [Paragraph("<b>DRIVERS</b>", styles['Normal']),
                 Paragraph("<b>Sum of Personal Conveyance (Duration)</b>", styles['Normal'])]
            ]
            for driver_name, duration in pc_data['drivers_list']:
                table_data.append([
                    Paragraph(driver_name, styles['Normal']),
                    Paragraph(duration, styles['Normal'])
                ])
            table_data.append([
                Paragraph("<b>Grand Total</b>", styles['Normal']),
                Paragraph(f"<b>{pc_data['grand_total']}</b>", styles['Normal'])
            ])

            from reportlab.platypus import TableStyle as RLTableStyle
            pc_table = Table(table_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
            pc_table.setStyle(RLTableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#B8CCE4')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('LINEBELOW', (0, -2), (-1, -2), 1, colors.black),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            story.append(pc_table)
            story.append(Spacer(1, 12))

            pc_bar_path = make_pc_usage_bar_chart(pc_df, tmpdir / "pc_bar.png")
            story.append(Spacer(1, 20))
            story.append(Image(str(pc_bar_path), width=400, height=250))

            story.append(Spacer(1, 20))
            story.append(Paragraph("<b>Insights:</b>", normal_bold))
            pc_insights = generate_pc_usage_insights(pc_data)
            pc_insights = convert_html_to_reportlab(pc_insights)
            story.append(Paragraph(pc_insights, styles['Normal']))
    except Exception as e:
        print(f"Error loading Personal Conveyance data: {e}")

    # Unassigned Driving Segments section
    try:
        unassigned_df = load_data(wiz_id, "unassigned_hos")
        if not unassigned_df.empty:
            story.append(Spacer(1, 30))

            try:
                # Generate summary data
                unassigned_data = generate_unassigned_driving_summary(
                    unassigned_df, end_date or pd.Timestamp.utcnow().date()
                )


                # Unassigned driving chart removed per new requirements
                # if unassigned_data.get('region_data'):
                #     unassigned_bar_path = make_unassigned_bar_chart(
                #         unassigned_df, tmpdir / "unassigned_bar.png"
                #     )
                #     story.append(Image(str(unassigned_bar_path), width=450, height=300))

                # Add insights regardless
                story.append(Spacer(1, 20))
                story.append(Paragraph("<b>Insights:</b>", normal_bold))
                first_insights = generate_unassigned_driving_insights(unassigned_data)
                first_insights = convert_html_to_reportlab(first_insights)
                story.append(Paragraph(first_insights, styles['Normal']))

                # Add section header and second insights
                story.append(Spacer(1, 30))
                story.append(Paragraph("<b>Unassigned Driving Segments</b>", section_title_style))
                story.append(Spacer(1, 12))
                story.append(Paragraph("<b>Insights:</b>", normal_bold))
                second_insights = generate_unassigned_segment_details(unassigned_data)
                second_insights = convert_html_to_reportlab(second_insights)
                story.append(Paragraph(second_insights, styles['Normal']))
            except Exception as e:
                print(f"Error processing Unassigned HOS data: {e}")
                # Add a placeholder message
                story.append(Paragraph("<b>Unassigned Driving Segments</b>", section_title_style))
                story.append(Paragraph("Unable to process unassigned driving data.", styles['Normal']))


    except Exception as e:
        print(f"Error loading Unassigned HOS data: {e}")

    # Driver Behavior & Speeding Analysis section
    try:
        driver_behaviors_df = load_data(wiz_id, "driver_behaviors")
        if not driver_behaviors_df.empty:
            story.append(PageBreak())
            story.append(Paragraph("<b>Driver Behavior & Speeding Analysis</b>", section_title_style))
            story.append(Spacer(1, 12))

            from .report_generator import generate_speeding_analysis_summary, generate_speeding_analysis_insights
            speeding_data = generate_speeding_analysis_summary(
                driver_behaviors_df, end_date or pd.Timestamp.utcnow().date()
            )

            story.append(Paragraph("<b>Insights:</b>", normal_bold))
            speeding_insights = generate_speeding_analysis_insights(speeding_data)
            speeding_insights = convert_html_to_reportlab(speeding_insights)
            story.append(Paragraph(speeding_insights, styles['Normal']))

    except Exception as e:
        print(f"Error loading Driver Behaviors data: {e}")

    # Missed DVIRs section
    try:
        mistdvi_df = load_data(wiz_id, "mistdvi")
        if not mistdvi_df.empty:
            story.append(Spacer(1, 30))
            story.append(Paragraph("<b>Missed DVIRs (Pre/Post Trip Reports)</b>", section_title_style))
            story.append(Spacer(1, 12))

            from .report_generator import generate_missed_dvir_summary, generate_missed_dvir_insights
            dvir_data = generate_missed_dvir_summary(
                mistdvi_df, end_date or pd.Timestamp.utcnow().date()
            )

            story.append(Paragraph("<b>Insights:</b>", normal_bold))
            dvir_insights = generate_missed_dvir_insights(dvir_data)
            dvir_insights = convert_html_to_reportlab(dvir_insights)
            story.append(Paragraph(dvir_insights, styles['Normal']))

            story.append(Spacer(1, 20))

            table_data = [
                [
                    Paragraph("<b>Driver</b>", styles['Normal']),
                    Paragraph("<b>POST-TRIP</b>", styles['Normal']),
                    Paragraph("<b>PRE-TRIP</b>", styles['Normal']),
                    Paragraph("<b>Grand Total</b>", styles['Normal'])
                ]
            ]

            for driver_data in dvir_data['top_drivers']:
                table_data.append([
                    Paragraph(driver_data['driver'], styles['Normal']),
                    Paragraph(str(driver_data['post_trip']), styles['Normal']),
                    Paragraph(str(driver_data['pre_trip']), styles['Normal']),
                    Paragraph(str(driver_data['total']), styles['Normal'])
                ])

            table_data.append([
                Paragraph("<b>Grand Total</b>", styles['Normal']),
                Paragraph(f"<b>{dvir_data['total_post_trip']}</b>", styles['Normal']),
                Paragraph(f"<b>{dvir_data['total_pre_trip']}</b>", styles['Normal']),
                Paragraph(f"<b>{dvir_data['total_missed']}</b>", styles['Normal'])
            ])

            from reportlab.platypus import TableStyle as RLTableStyle
            dvir_table = Table(
                table_data,
                colWidths=[doc.width * 0.4, doc.width * 0.2, doc.width * 0.2, doc.width * 0.2]
            )
            dvir_table.setStyle(RLTableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#B8CCE4')),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#B8CCE4')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            story.append(dvir_table)

    except Exception as e:
        print(f"Error loading Missed DVIR data: {e}")

    doc.build(story)
    return out_path

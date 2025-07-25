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
from reportlab.lib.units import inch

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
    generate_dot_risk_assessment,
)

from .visualizations.chart_factory import (
    make_stacked_bar,
    make_trend_line,
    make_pc_usage_bar_chart,
    make_safety_events_bar,
    make_unassigned_segments_visual,
    make_speeding_pie_chart,
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
    create_dashboard: bool = False,
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

    # placeholders for later sections
    safety_inbox_data = None
    pc_data = None
    unassigned_data = None
    speeding_data = None
    dvir_data = None

    end_date = pd.to_datetime(trend_end).date() if trend_end else None
    bar_path = make_stacked_bar(df, tmpdir / "bar.png")
    trend_path = make_trend_line(df, end_date, tmpdir / "trend.png")

    # Generate additional dashboard charts
    try:
        safety_df = load_data(wiz_id, "safety_inbox")
    except Exception as e:
        print(f"Error loading safety inbox data for chart: {e}")
        safety_df = pd.DataFrame()

    safety_chart_path = make_safety_events_bar(
        safety_df, tmpdir / "safety_events.png"
    )

    try:
        unassigned_df_chart = load_data(wiz_id, "unassigned_hos")
    except Exception as e:
        print(f"Error loading unassigned HOS data for chart: {e}")
        unassigned_df_chart = pd.DataFrame()

    unassigned_chart_path = make_unassigned_segments_visual(
        unassigned_df_chart, tmpdir / "unassigned_segments.png"
    )

    try:
        driver_behaviors_df_chart = load_data(wiz_id, "driver_behaviors")
    except Exception:
        driver_behaviors_df_chart = pd.DataFrame()

    try:
        mistdvi_df_chart = load_data(wiz_id, "mistdvi")
    except Exception:
        mistdvi_df_chart = pd.DataFrame()

    speeding_source_df = (
        driver_behaviors_df_chart if not driver_behaviors_df_chart.empty else mistdvi_df_chart
    )

    speeding_chart_path = make_speeding_pie_chart(
        speeding_source_df, tmpdir / "speeding_events.png"
    )

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
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=LETTER,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#000000'),
        spaceAfter=10,
        alignment=1,  # Center alignment
        fontName='Helvetica-Bold'
    )

    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#000000'),
        spaceAfter=8,
        spaceBefore=12
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

    # Create custom header section
    from reportlab.platypus import Table as RLTable
    from reportlab.platypus import TableStyle as RLTableStyle

    # Add logo/graphic placeholder (the red scribble design)
    logo_placeholder = Spacer(1, 50)  # Replace with Image('path/to/logo.png', width=100, height=50)

    # Main title
    story.append(Paragraph("DOT COMPLIANCE SNAPSHOT", title_style))
    story.append(Spacer(1, 12))

    # Create the date/location/position table
    header_end_date = end_date or pd.Timestamp.utcnow().date()
    start_date = header_end_date - pd.Timedelta(days=header_end_date.weekday())
    end_date_display = start_date + pd.Timedelta(days=6)

    date_range_str = f"{start_date.strftime('%m/%d/%Y')} – {end_date_display.strftime('%m/%d/%Y')}"

    header_data = [
        [
            Paragraph(f"<b>Date:</b> {header_end_date.strftime('%B %d, %Y')}", styles['Normal']),
            Paragraph("<b>Location:</b> All Regions", styles['Normal'])
        ],
        [
            Paragraph("<b>Discussion Type:</b> DOT Compliance", styles['Normal']),
            Paragraph("<b>Job Positions:</b> Field Crew", styles['Normal'])
        ]
    ]

    header_table = RLTable(header_data, colWidths=[doc.width * 0.5, doc.width * 0.5])
    header_table.setStyle(RLTableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))

    story.append(header_table)
    story.append(Spacer(1, 12))

    # Add the fleet safety snapshot subtitle with date range
    fleet_snapshot_title = Paragraph(
        f"<b>DOT Fleet Safety Snapshot: {date_range_str}</b>",
        ParagraphStyle(
            'FleetSnapshotTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#000000'),
            alignment=1,  # Center
            spaceAfter=20
        )
    )
    story.append(fleet_snapshot_title)
    story.append(Spacer(1, 12))

    chart_paths = {
        "hos_violation": bar_path,
        "trend": trend_path,
        "safety_events": safety_chart_path,
        "unassigned_segments": unassigned_chart_path,
        "speeding_events": speeding_chart_path,
    }

    if create_dashboard:
        story.append(Paragraph("<b>Visual Dashboard</b>", section_title_style))
        story.append(Spacer(1, 12))

        chart_data = []
        row1 = []
        row2 = []
        row3 = []

        if "hos_violation" in chart_paths:
            row1.append(Image(str(chart_paths["hos_violation"]), width=3.5 * inch, height=2 * inch))
        if "trend" in chart_paths:
            row1.append(Image(str(chart_paths["trend"]), width=3.5 * inch, height=2 * inch))

        if "safety_events" in chart_paths:
            row2.append(Image(str(chart_paths["safety_events"]), width=3.5 * inch, height=2 * inch))
        if "unassigned_segments" in chart_paths:
            row2.append(Image(str(chart_paths["unassigned_segments"]), width=3.5 * inch, height=2 * inch))

        if "speeding_events" in chart_paths:
            row3.append(Image(str(chart_paths["speeding_events"]), width=3.5 * inch, height=2 * inch))
        row3.append(Spacer(3.5 * inch, 2 * inch))

        chart_data = [row1, row2, row3] if row1 else []

        if chart_data:
            chart_table = Table(chart_data, colWidths=[3.5 * inch, 3.5 * inch])
            chart_table.setStyle(RLTableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(chart_table)

        story.append(PageBreak())

    # PAGE 1: HOS Violations Charts
    story.append(Paragraph("<b>HOS Violations Analysis</b>", section_title_style))
    story.append(Spacer(1, 12))

    if "hos_violation" in chart_paths:
        img = Image(str(chart_paths["hos_violation"]), width=5 * inch, height=3 * inch)
        story.append(img)
        story.append(Spacer(1, 12))

    if "trend" in chart_paths:
        img = Image(str(chart_paths["trend"]), width=5 * inch, height=3 * inch)
        story.append(img)

    story.append(PageBreak())

    # PAGE 2: Safety Events and Unassigned Driving
    story.append(Paragraph("<b>Safety Events and Unassigned Driving Analysis</b>", section_title_style))
    story.append(Spacer(1, 12))

    if "safety_events" in chart_paths:
        img = Image(str(chart_paths["safety_events"]), width=5 * inch, height=3 * inch)
        story.append(img)
        story.append(Spacer(1, 12))

    if "unassigned_segments" in chart_paths:
        img = Image(str(chart_paths["unassigned_segments"]), width=6 * inch, height=3 * inch)
        story.append(img)

    story.append(PageBreak())

    # PAGE 3: Speeding Analysis
    story.append(Paragraph("<b>Speeding Events Analysis</b>", section_title_style))
    story.append(Spacer(1, 12))

    if "speeding_events" in chart_paths:
        img = Image(str(chart_paths["speeding_events"]), width=4 * inch, height=4 * inch)
        data = [[img]]
        t = Table(data, colWidths=[doc.width])
        t.setStyle(RLTableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(t)

    story.append(PageBreak())

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
    story.append(Spacer(1, 12))

    # Summary Insights section
    story.append(Paragraph("<b>Insights:</b>", normal_bold))
    story.append(Paragraph(summary_insights, styles['Normal']))
    story.append(Spacer(1, 12))

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
            story.append(Spacer(1, 12))
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
            story.append(Spacer(1, 12))

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
            story.append(Spacer(1, 12))
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
            story.append(Spacer(1, 12))
            story.append(Image(str(pc_bar_path), width=400, height=250))

            story.append(Spacer(1, 12))
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
            story.append(Spacer(1, 12))

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
                story.append(Spacer(1, 12))
                story.append(Paragraph("<b>Insights:</b>", normal_bold))
                first_insights = generate_unassigned_driving_insights(unassigned_data)
                first_insights = convert_html_to_reportlab(first_insights)
                story.append(Paragraph(first_insights, styles['Normal']))

                # Add section header and second insights
                story.append(Spacer(1, 12))
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
        driver_safety_df = load_data(wiz_id, "driver_safety")

        # Process if either dataset exists
        if not driver_behaviors_df.empty or not driver_safety_df.empty:
            story.append(PageBreak())
            story.append(Paragraph("<b>Driver Behavior & Speeding Analysis</b>", section_title_style))
            story.append(Spacer(1, 12))

            # Generate summary data from both sources
            from .report_generator import generate_speeding_analysis_summary, generate_speeding_analysis_insights
            speeding_data = generate_speeding_analysis_summary(
                driver_behaviors_df,
                driver_safety_df,
                end_date or pd.Timestamp.utcnow().date()
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
            story.append(Spacer(1, 12))
            story.append(Paragraph("<b>Missed DVIRs (Pre/Post Trip Reports)</b>", section_title_style))
            story.append(Spacer(1, 12))

            # Generate summary data
            from .report_generator import generate_missed_dvir_summary, generate_missed_dvir_insights
            dvir_data = generate_missed_dvir_summary(mistdvi_df, end_date or pd.Timestamp.utcnow().date())

            # Add DVIR table FIRST
            # Create table data
            table_data = [
                [Paragraph("<b>Driver</b>", styles['Normal']),
                 Paragraph("<b>POST-TRIP</b>", styles['Normal']),
                 Paragraph("<b>PRE-TRIP</b>", styles['Normal']),
                 Paragraph("<b>Grand Total</b>", styles['Normal'])]
            ]

            for driver_data in dvir_data['top_drivers']:
                table_data.append([
                    Paragraph(driver_data['driver'], styles['Normal']),
                    Paragraph(str(driver_data['post_trip']), styles['Normal']),
                    Paragraph(str(driver_data['pre_trip']), styles['Normal']),
                    Paragraph(str(driver_data['total']), styles['Normal'])
                ])

            # Add grand total row
            table_data.append([
                Paragraph("<b>Grand Total</b>", styles['Normal']),
                Paragraph(f"<b>{dvir_data['total_post_trip']}</b>", styles['Normal']),
                Paragraph(f"<b>{dvir_data['total_pre_trip']}</b>", styles['Normal']),
                Paragraph(f"<b>{dvir_data['total_missed']}</b>", styles['Normal'])
            ])

            from reportlab.platypus import TableStyle as RLTableStyle
            dvir_table = Table(table_data, colWidths=[doc.width * 0.4, doc.width * 0.2, doc.width * 0.2, doc.width * 0.2])
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

            # Add insights AFTER the table
            story.append(Spacer(1, 12))
            story.append(Paragraph("<b>Insights:</b>", normal_bold))
            dvir_insights = generate_missed_dvir_insights(dvir_data)
            dvir_insights = convert_html_to_reportlab(dvir_insights)
            story.append(Paragraph(dvir_insights, styles['Normal']))

    except Exception as e:
        print(f"Error loading Missed DVIR data: {e}")

    # Overall DOT Risk Assessment section
    story.append(PageBreak())
    story.append(Paragraph("<b>Overall DOT Risk Assessment</b>", section_title_style))
    story.append(Spacer(1, 12))

    risk_assessment = generate_dot_risk_assessment(
        summary_data,
        safety_inbox_data if 'safety_inbox_data' in locals() else None,
        pc_data if 'pc_data' in locals() else None,
        unassigned_data if 'unassigned_data' in locals() else None,
        speeding_data if 'speeding_data' in locals() else None,
        dvir_data if 'dvir_data' in locals() else None,
    )

    risk_assessment = risk_assessment.replace('####', '').replace('###', '')
    risk_assessment = re.sub(
        r"(overall DOT risk level is assessed as\s*)(High|Medium|Low)",
        lambda m: m.group(1) + f"<b>{m.group(2)}</b>",
        risk_assessment,
        flags=re.IGNORECASE,
    )
    risk_assessment = convert_html_to_reportlab(risk_assessment)

    story.append(Paragraph(risk_assessment, styles['Normal']))

    doc.build(story)
    return out_path

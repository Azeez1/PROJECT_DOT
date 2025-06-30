import os
from functools import lru_cache
import json
from datetime import date
from typing import Dict

import pandas as pd
from openai import OpenAI

from .visualizations.chart_factory import normalize_violation_types

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPEN_API_KEY"))


def _standardize_columns(df: pd.DataFrame) -> dict:
    """Return mapping of normalized column names to actual names."""
    return {c.strip().lower().replace(" ", "_"): c for c in df.columns}


def _monday_of(day: date) -> date:
    ts = pd.Timestamp(day)
    return (ts - pd.Timedelta(days=ts.weekday())).date()


def generate_hos_violations_summary(df: pd.DataFrame, trend_end_date: date) -> Dict:
    """Return week-over-week summary statistics for HOS violations."""
    cols = _standardize_columns(df)
    week_col = cols.get("week") or next((c for k, c in cols.items() if k.startswith("week")), None)
    tag_col = cols.get("tags")
    vt_col = cols.get("violation_type")
    if not week_col:
        raise ValueError("Week column required for summary")
    if vt_col:
        df[vt_col] = normalize_violation_types(df[vt_col])
    df["week"] = pd.to_datetime(df[week_col])

    current_start = pd.Timestamp(_monday_of(trend_end_date))
    previous_start = current_start - pd.Timedelta(weeks=1)
    previous_end = current_start - pd.Timedelta(days=1)

    current = df[(df["week"] >= current_start) & (df["week"] <= current_start + pd.Timedelta(days=6))]
    previous = df[(df["week"] >= previous_start) & (df["week"] <= previous_end)]

    total_current = len(current)
    total_previous = len(previous)
    total_change = total_current - total_previous

    region_lookup = {
        "great lakes": "Great Lakes",
        "ohio valley": "Ohio Valley",
        "midwest": "Midwest",
        "southeast": "Southeast",
    }
    by_region = {}
    if tag_col:
        cur_reg = current[tag_col].astype(str).str.strip().str.lower().map(region_lookup)
        prev_reg = previous[tag_col].astype(str).str.strip().str.lower().map(region_lookup)
        for region in region_lookup.values():
            cur_count = int((cur_reg == region).sum())
            prev_count = int((prev_reg == region).sum())
            if cur_count or prev_count:
                by_region[region] = {"current": cur_count, "change": cur_count - prev_count}

    by_type = {}
    if vt_col:
        cur_counts = current[vt_col].value_counts()
        prev_counts = previous[vt_col].value_counts()
        for vt in cur_counts.index.union(prev_counts.index):
            cur = int(cur_counts.get(vt, 0))
            prev = int(prev_counts.get(vt, 0))
            by_type[vt] = {"current": cur, "change": cur - prev}
        by_type = dict(sorted(by_type.items(), key=lambda x: x[1]["current"], reverse=True))

    summary = {
        "total_current": int(total_current),
        "total_previous": int(total_previous),
        "total_change": int(total_change),
        "by_region": by_region,
        "by_type": by_type,
    }

    print(f"DEBUG: summary_data = {summary}")
    print("DEBUG: Calling generate_summary_insights...")

    return summary


def generate_hos_trend_analysis(df: pd.DataFrame, trend_end_date: date) -> Dict:
    """Return 4-week trend data grouped by violation type."""
    cols = _standardize_columns(df)
    week_col = cols.get("week") or next((c for k, c in cols.items() if k.startswith("week")), None)
    vt_col = cols.get("violation_type")
    if not week_col or not vt_col:
        raise ValueError("Week and violation_type columns required for trend analysis")

    df[vt_col] = normalize_violation_types(df[vt_col])
    df["week"] = pd.to_datetime(df[week_col])

    end_monday = pd.Timestamp(_monday_of(trend_end_date))
    weeks = [end_monday - pd.Timedelta(weeks=i) for i in reversed(range(4))]
    df["week_of"] = (df["week"] - pd.to_timedelta(df["week"].dt.weekday, unit="D")).dt.date
    df2 = df[df["week_of"].isin([w.date() for w in weeks])]

    pivot = (
        df2.groupby(["week_of", vt_col]).size().unstack(fill_value=0)
        .reindex(index=[w.date() for w in weeks], fill_value=0)
    )

    return {
        "weeks": [w.date().isoformat() for w in weeks],
        "data": {col: pivot[col].astype(int).tolist() for col in pivot.columns},
    }


def format_regional_data(data: Dict[str, Dict[str, int]]) -> str:
    lines = []
    for region, values in data.items():
        sign = "+" if values["change"] >= 0 else ""
        lines.append(f"{region}: {values['current']} ({sign}{values['change']})")
    return "\n".join(lines)


def format_violation_types(data: Dict[str, Dict[str, int]]) -> str:
    lines = []
    for vt, values in data.items():
        sign = "+" if values["change"] >= 0 else ""
        lines.append(f"{vt}: {values['current']} ({sign}{values['change']})")
    return "\n".join(lines)


def format_trend_data(trend: Dict) -> str:
    lines = []
    weeks = trend.get("weeks", [])
    for vt, counts in trend.get("data", {}).items():
        joined = ", ".join(str(c) for c in counts)
        lines.append(f"{vt}: {joined}")
    if weeks:
        lines.insert(0, "Weeks: " + ", ".join(weeks))
    return "\n".join(lines)


def _make_summary_key(data: Dict) -> str:
    """Return a stable JSON string for caching."""
    return json.dumps(data, sort_keys=True)


@lru_cache(maxsize=None)
def _cached_summary_insights(summary_json: str) -> str:
    """Generate insights for weekly summary using OpenAI."""
    summary_data: Dict = json.loads(summary_json)
    try:
        if not os.environ.get("OPEN_API_KEY"):
            print("WARNING: No OpenAI API key found, using fallback")
            return generate_fallback_summary_insights(summary_data)

        prompt = f"""Analyze this HOS violations data and provide 2-3 sentences of insights:

        Total Violations: {summary_data['total_current']} ({summary_data['total_change']:+})
        Previous Week: {summary_data['total_previous']} → This Week: {summary_data['total_current']}

        Regional Changes:
        {format_regional_data(summary_data.get('by_region', {}))}

        Top Violation Types:
        {format_violation_types(summary_data.get('by_type', {}))}

        Focus on: overall trend, regional patterns, concerning violations, and positive developments."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7,
        )
        insights = response.choices[0].message.content.strip()
        print(f"DEBUG: Generated insights: {insights}")
        return insights
    except Exception as e:
        print(f"ERROR in generate_summary_insights: {e}")
        return generate_fallback_summary_insights(summary_data)


def generate_summary_insights(summary_data: Dict) -> str:
    summary_json = _make_summary_key(summary_data)
    return _cached_summary_insights(summary_json)


def generate_fallback_summary_insights(summary_data: Dict) -> str:
    """Fallback summary analysis when OpenAI is unavailable."""
    total_change = summary_data.get("total_change", 0)
    trend = (
        "increased" if total_change > 0 else "decreased" if total_change < 0 else "remained stable"
    )

    by_region = summary_data.get("by_region", {})
    biggest_change_region = None
    biggest_change = 0
    for region, data in by_region.items():
        if abs(data.get("change", 0)) > abs(biggest_change):
            biggest_change = data.get("change", 0)
            biggest_change_region = region

    by_type = summary_data.get("by_type", {})
    top_violation = None
    top_count = 0
    for vt, data in by_type.items():
        if data.get("current", 0) > top_count:
            top_count = data.get("current", 0)
            top_violation = vt

    insights = (
        f"Although the total number of violations {trend} to {summary_data.get('total_current', 0)}, "
        "the distribution reflects regional variability. "
    )

    if biggest_change_region:
        change_word = "improved" if biggest_change < 0 else "saw an increase"
        insights += f"{biggest_change_region} {change_word} by {abs(biggest_change)}. "

    if top_violation:
        insights += f"{top_violation} remains the top issue at {top_count}. "

    return insights


def _make_trend_key(data: Dict) -> str:
    return json.dumps(data, sort_keys=True)


@lru_cache(maxsize=None)
def _cached_trend_insights(trend_json: str) -> str:
    """Generate insights for 4-week trend using OpenAI."""
    trend_data: Dict = json.loads(trend_json)
    try:
        if not os.environ.get("OPEN_API_KEY"):
            print("WARNING: No OpenAI API key found, using fallback")
            return generate_fallback_trend_insights(trend_data)

        trends_text = format_trend_data(trend_data)

        prompt = f"""Analyze this 4-week HOS violation trend data and provide insights in a single paragraph:

        {trends_text}

        Provide a comprehensive analysis covering:
        1. Key patterns and trends for each violation type
        2. Notable improvements or deteriorations
        3. Areas of concern that need attention

        Keep the response as a single, complete paragraph without line breaks."""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.7,
        )
        insights = response.choices[0].message.content.strip()
        print(f"DEBUG: Generated trend insights: {insights}")
        return insights
    except Exception as e:
        print(f"ERROR in generate_trend_insights: {e}")
        return generate_fallback_trend_insights(trend_data)


def generate_trend_insights(trend_data: Dict) -> str:
    trend_json = _make_trend_key(trend_data)
    return _cached_trend_insights(trend_json)


def generate_fallback_trend_insights(trend_data: Dict) -> str:
    return "Trend analysis not available."


def generate_safety_inbox_summary(df: pd.DataFrame, trend_end_date: date) -> Dict:
    """Generate Safety Inbox Events summary statistics."""
    cols = _standardize_columns(df)

    # Normalize column names we'll be using
    event_type_col = cols.get("event_type")
    status_col = cols.get("status")
    driver_tags_col = cols.get("driver_tags")
    time_col = cols.get("time")

    # Filter to current week if time column exists
    if time_col:
        df["time"] = pd.to_datetime(df[time_col], errors='coerce')
        current_start = pd.Timestamp(_monday_of(trend_end_date))
        previous_start = current_start - pd.Timedelta(weeks=1)

        current_week = df[(df["time"] >= current_start) & (df["time"] <= current_start + pd.Timedelta(days=6))]
        previous_week = df[(df["time"] >= previous_start) & (df["time"] < current_start)]
    else:
        # If no time column, use all data
        current_week = df
        previous_week = pd.DataFrame()  # Empty for comparison

    # Total events
    total_current = len(current_week)
    total_previous = len(previous_week)
    total_change = total_current - total_previous

    # Dismissed events
    dismissed_count = 0
    if status_col and 'dismissed' in current_week[status_col].str.lower().values:
        dismissed_count = (current_week[status_col].str.lower() == 'dismissed').sum()

    # Region breakdown
    region_lookup = {
        "great lakes": "Great Lakes",
        "ohio valley": "Ohio Valley",
        "midwest": "Midwest",
        "southeast": "Southeast",
        "corporate": "Corporate",
    }

    by_region = {}
    if driver_tags_col:
        for region_key, region_name in region_lookup.items():
            mask = current_week[driver_tags_col].astype(str).str.lower().str.contains(region_key.replace(" ", "|"), na=False)
            count = mask.sum()
            if count > 0:
                by_region[region_name] = int(count)

    # Event type breakdown
    event_breakdown = {}
    if event_type_col:
        # Normalize event types
        current_week = current_week.copy()
        current_week['event_type_normalized'] = current_week[event_type_col].astype(str).str.strip()
        event_counts = current_week['event_type_normalized'].value_counts()

        # Map to standard event names
        event_mapping = {
            'crash': 'Crash',
            'defensive driving': 'Defensive Driving',
            'following distance': 'Following Distance',
            'forward collision warning': 'Forward Collision Warning',
            'harsh accel': 'Harsh Accel',
            'harsh brake': 'Harsh Brake',
            'harsh turn': 'Harsh Turn',
            'inattentive driving': 'Inattentive Driving',
        }

        for event, count in event_counts.items():
            event_lower = event.lower()
            for key, display_name in event_mapping.items():
                if key in event_lower:
                    # Check if dismissed
                    if status_col:
                        dismissed = (
                            (current_week['event_type_normalized'] == event)
                            & (current_week[status_col].str.lower() == 'dismissed')
                        ).sum()
                        if dismissed == count:
                            event_breakdown[display_name] = f"{count} (dismissed)"
                        else:
                            event_breakdown[display_name] = str(count)
                    else:
                        event_breakdown[display_name] = str(count)
                    break

    # Fill in missing event types with 0
    all_event_types = [
        'Crash',
        'Defensive Driving',
        'Following Distance',
        'Forward Collision Warning',
        'Harsh Accel',
        'Harsh Brake',
        'Harsh Turn',
        'Inattentive Driving',
    ]
    for event_type in all_event_types:
        if event_type not in event_breakdown:
            event_breakdown[event_type] = "0"

    return {
        "total_current": total_current,
        "total_change": total_change,
        "dismissed_count": dismissed_count,
        "by_region": by_region,
        "event_breakdown": event_breakdown,
    }


def generate_safety_inbox_insights(summary_data: Dict) -> str:
    """Generate insights for Safety Inbox Events using OpenAI or fallback."""
    try:
        if not os.environ.get("OPEN_API_KEY"):
            return generate_fallback_safety_inbox_insights(summary_data)

        # Format the data for the prompt
        region_text = "\n".join([f"   o {region}: {count}" for region, count in summary_data['by_region'].items()])
        event_text = "\n".join([f"   • {event}: {count}" for event, count in summary_data['event_breakdown'].items()])

        prompt = f"""Analyze this Safety Inbox Events data and provide insights in 2-3 sentences:

        Total Safety Events: {summary_data['total_current']} ({summary_data['total_change']:+})
        Dismissed: {summary_data['dismissed_count']}

        Breakdown by Region:
        {region_text}

        Event Breakdown:
        {event_text}

        Focus on: dismissal patterns, dominant event types, regional distribution, and any concerning trends."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERROR in generate_safety_inbox_insights: {e}")
        return generate_fallback_safety_inbox_insights(summary_data)


def generate_fallback_safety_inbox_insights(summary_data: Dict) -> str:
    """Fallback insights for Safety Inbox when OpenAI is unavailable."""
    total = summary_data['total_current']
    dismissed = summary_data['dismissed_count']

    # Find dominant event type
    event_breakdown = summary_data['event_breakdown']
    non_zero_events = [(k, v) for k, v in event_breakdown.items() if v != "0" and "dismissed" not in v]

    if dismissed == total and total > 0:
        insights = f"All {total} safety events this week were dismissed, indicating no actionable violations. "
    else:
        insights = f"Of {total} total safety events, {dismissed} were dismissed. "

    if non_zero_events:
        dominant_event = max(non_zero_events, key=lambda x: int(x[1].split()[0]))
        insights += f"The most common event type was {dominant_event[0]} with {dominant_event[1]} occurrences. "

    # Regional distribution
    regions = list(summary_data['by_region'].keys())
    if len(regions) > 1:
        insights += f"Events were distributed across {', '.join(regions[:-1])} and {regions[-1]}."
    elif regions:
        insights += f"All events occurred in the {regions[0]} region."

    return insights


def generate_pc_usage_summary(df: pd.DataFrame, trend_end_date: date) -> Dict:
    """Generate Personal Conveyance usage summary for drivers with 3+ hours in current week."""
    cols = _standardize_columns(df)

    # Find relevant columns
    driver_col = None
    duration_col = None
    date_col = None

    for col in df.columns:
        col_lower = col.lower()
        if "driver" in col_lower:
            driver_col = col
        if any(term in col_lower for term in ["personal conveyance", "pc duration", "sum of personal"]):
            duration_col = col
        if "date" in col_lower:
            date_col = col

    if not driver_col or not duration_col:
        raise ValueError(f"Required columns not found. Available: {list(df.columns)}")

    # Filter to current week if a date column exists
    if date_col:
        df = df.copy()
        df["date"] = pd.to_datetime(df[date_col], errors="coerce")
        current_start = pd.Timestamp(_monday_of(trend_end_date))
        current_end = current_start + pd.Timedelta(days=6)
        df = df[(df["date"] >= current_start) & (df["date"] <= current_end)]

    # Aggregate durations per driver
    if date_col and len(df) > 0:
        # Group by driver and aggregate durations manually
        driver_groups = df.groupby(driver_col)[duration_col].apply(list).reset_index()
        driver_groups['total_duration'] = driver_groups[duration_col].apply(sum_pc_durations)
        aggregated = driver_groups[[driver_col, 'total_duration']]
    else:
        aggregated = df[[driver_col, duration_col]].copy()
        aggregated["total_duration"] = aggregated[duration_col].apply(lambda d: sum_pc_durations([d]))

    drivers_list = []
    total_seconds = 0

    for _, row in aggregated.iterrows():
        driver = row[driver_col]
        seconds = row["total_duration"]
        hours = seconds / 3600
        if hours >= 3:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            duration_str = f"{h}:{m:02d}:{s:02d}"
            drivers_list.append((driver, duration_str))
            total_seconds += seconds

    driver_totals_map = dict(zip(aggregated[driver_col], aggregated["total_duration"]))
    drivers_list.sort(key=lambda x: driver_totals_map.get(x[0], 0), reverse=True)

    total_hours = int(total_seconds // 3600)
    total_minutes = int((total_seconds % 3600) // 60)
    total_secs = int(total_seconds % 60)
    grand_total = f"{total_hours}:{total_minutes:02d}:{total_secs:02d}"

    return {
        "total_pc_time": grand_total,
        "drivers_list": drivers_list,
        "exceeded_daily_limit_count": len(drivers_list),
        "grand_total": grand_total,
    }


def generate_pc_usage_insights(summary_data: Dict) -> str:
    """Generate insights for Personal Conveyance usage."""
    total_time = summary_data.get('total_pc_time', '0:00:00')
    drivers_list = summary_data.get('drivers_list', [])
    exceeded_count = summary_data.get('exceeded_daily_limit_count', 0)

    try:
        if not os.environ.get("OPEN_API_KEY"):
            return generate_fallback_pc_insights(summary_data)

        driver_text = "\n".join([f"- {driver}: {duration}" for driver, duration in drivers_list[:5]])

        prompt = f"""Analyze this Personal Conveyance usage data and provide insights in 2-3 sentences:

        Total PC Time: {total_time}
        Drivers exceeding 3 hours/day: {exceeded_count}

        Top PC Users:
        {driver_text}

        Focus on: compliance with 2hr/day and 14hr/week limits, patterns of excessive use, and recommendations."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERROR in generate_pc_usage_insights: {e}")
        return generate_fallback_pc_insights(summary_data)


def generate_fallback_pc_insights(summary_data: Dict) -> str:
    """Fallback PC insights when OpenAI is unavailable."""
    drivers_list = summary_data.get('drivers_list', [])
    exceeded_count = summary_data.get('exceeded_daily_limit_count', 0)

    insights = f"A total of {exceeded_count} drivers exceeded the recommended 3 hours of Personal Conveyance in a single day. "

    if drivers_list:
        top_driver = drivers_list[0]
        insights += f"The highest usage was by {top_driver[0]} with {top_driver[1]} hours. "

    insights += "Continued monitoring is recommended to ensure compliance with the 2 hour/day and 14 hour/week PC limits to avoid potential HOS violations."

    return insights


def sum_pc_durations(durations):
    """Sum multiple Personal Conveyance duration strings to seconds."""
    total_seconds = 0
    for duration in durations:
        if pd.notna(duration) and ':' in str(duration):
            parts = str(duration).split(':')
            if len(parts) >= 3:
                h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
                total_seconds += h * 3600 + m * 60 + s
    return total_seconds


def generate_unassigned_driving_summary(df: pd.DataFrame, trend_end_date: date) -> Dict:
    """Process unassigned driving data dynamically."""
    # Debug: show available columns for troubleshooting various formats
    print(f"DEBUG Unassigned HOS columns: {list(df.columns)}")

    cols = _standardize_columns(df)

    # Use flexible matching to locate relevant columns
    vehicle_col = None
    driver_col = None
    segments_col = None
    time_col = None
    tags_col = None

    for col in df.columns:
        col_lower = col.lower()
        if "vehicle" in col_lower:
            vehicle_col = col
        if "driver" in col_lower or "owner" in col_lower:
            driver_col = col
        if "segment" in col_lower and "unassigned" in col_lower:
            segments_col = col
        if "time" in col_lower and "unassigned" in col_lower:
            time_col = col
        if "tag" in col_lower:
            tags_col = col

    # Ensure we have at least time or segment data
    if not time_col and not segments_col:
        raise ValueError(
            f"Cannot find unassigned time or segments columns. Available: {list(df.columns)}"
        )

    if "date" in cols:
        df = df.copy()
        df["date"] = pd.to_datetime(df[cols["date"]], errors="coerce")
        current_start = pd.Timestamp(_monday_of(trend_end_date))
        previous_start = current_start - pd.Timedelta(weeks=1)

        current_week = df[(df["date"] >= current_start) & (df["date"] <= current_start + pd.Timedelta(days=6))].copy()
        previous_week = df[(df["date"] >= previous_start) & (df["date"] < current_start)].copy()
    else:
        current_week = df.copy()
        previous_week = pd.DataFrame()

    total_segments = int(current_week[segments_col].sum()) if segments_col else len(current_week)
    prev_segments = int(previous_week[segments_col].sum()) if segments_col and not previous_week.empty else 0
    total_change = total_segments - prev_segments

    region_data: Dict[str, Dict[str, int | float]] = {}
    region_mapping = {
        "great lakes": "Great Lakes",
        "ohio valley": "Ohio Valley",
        "southeast": "Southeast",
        "gl": "Great Lakes",
        "ov": "Ohio Valley",
        "se": "Southeast",
    }

    for region_key, region_name in region_mapping.items():
        if tags_col:
            mask = current_week[tags_col].str.lower().str.contains(region_key, na=False)
            if mask.any():
                region_df = current_week[mask]

                # Calculate time for this region
                if time_col:
                    total_seconds = 0
                    for time_str in region_df[time_col]:
                        if pd.notna(time_str) and ':' in str(time_str):
                            parts = str(time_str).split(':')
                            if len(parts) == 3:
                                try:
                                    h = int(parts[0])
                                    m = int(parts[1])
                                    # Support decimal seconds
                                    s = float(parts[2])
                                    total_seconds += h * 3600 + m * 60 + s
                                except ValueError as e:
                                    print(f"Error parsing time '{time_str}': {e}")
                                    continue

                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    seconds = int(total_seconds % 60)
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                    region_data[region_name] = {
                        'time_str': time_str,
                        'total_seconds': total_seconds,
                        'segments': int(region_df[segments_col].sum()) if segments_col else len(region_df)
                    }

    top_contributors = []
    if vehicle_col and driver_col and segments_col:
        contributor_df = (
            current_week.groupby([vehicle_col, driver_col, tags_col])[segments_col]
            .sum()
            .reset_index()
        )
        contributor_df = contributor_df.sort_values(segments_col, ascending=False)
        for _, row in contributor_df.head(5).iterrows():
            region = "Unknown"
            if pd.notna(row[tags_col]):
                for k, v in region_mapping.items():
                    if k in str(row[tags_col]).lower():
                        region = v
                        break
            top_contributors.append(
                {
                    "vehicle": row[vehicle_col],
                    "driver": row[driver_col],
                    "segments": int(row[segments_col]),
                    "region": region,
                }
            )

    return {
        "total_segments": total_segments,
        "total_change": total_change,
        "region_data": region_data,
        "top_contributors": top_contributors,
    }





def generate_unassigned_driving_insights(summary_data: Dict) -> str:
    """Generate insights dynamically based on actual data."""
    total = summary_data.get("total_segments", 0)
    change = summary_data.get("total_change", 0)
    contributors = summary_data.get("top_contributors", [])

    if total == 0:
        return (
            "No unassigned driving segments were recorded this week, "
            "indicating full compliance with login procedures."
        )

    insights = (
        f"Unassigned driving segments {'rose to' if change > 0 else 'fell to'} "
        f"{total} this week, "
    )
    if change != 0:
        insights += f"{'up' if change > 0 else 'down'} from the previous reporting period. "
    else:
        insights += "unchanged from the previous period. "

    if contributors:
        main = contributors[0]
        insights += (
            f"The majority of these segments ({main['segments']}) are tied to {main['vehicle']} "
            f"in the {main['region']} and attributed to <b>{main['driver']}</b>, "
            "indicating a likely pattern of non-login or shared use. "
        )
        if len(contributors) > 1:
            others = []
            for contrib in contributors[1:4]:
                others.append(f"<b>{contrib['driver']}</b> ({contrib['segments']} segments)")
            if others:
                insights += f"Other contributors include {', '.join(others)} across their respective regions. "

    insights += (
        "This pattern suggests localized procedural breakdowns that may be resolved through "
        "targeted driver login reminders, training refreshers, and reinforcing expectations "
        "for system use during early shifts or maintenance movements. "
        "Continued monitoring is recommended to prevent this trend from escalating."
    )
    return insights


def generate_fallback_unassigned_driving_insights(summary_data: Dict) -> str:
    change = summary_data.get("total_change", 0)
    if change > 0:
        trend = f"rose by {change}"
    elif change < 0:
        trend = f"fell by {abs(change)}"
    else:
        trend = "remained stable"

    top = summary_data.get("top_contributors", [])
    names = ", ".join(item.get("driver") for item in top)
    return (
        f"Unassigned driving segments {trend} to {summary_data.get('total_segments', 0)}. "
        f"Top contributors include {names}. Consider reinforcing login procedures."
    )


def generate_unassigned_segment_details(summary_data: Dict) -> str:
    """Generate detailed insights about specific vehicles and drivers."""
    total = summary_data.get('total_segments', 0)
    contributors = summary_data.get('top_contributors', [])

    if total == 0:
        return "No unassigned driving segments were recorded this week."

    insights = f"A total of {total} unassigned driving segments were recorded this week, "

    vehicle_data: Dict[str, list] = {}
    for contrib in contributors:
        vehicle = contrib['vehicle']
        if vehicle not in vehicle_data:
            vehicle_data[vehicle] = []
        vehicle_data[vehicle].append(contrib)

    insights += f"all attributable to {len(vehicle_data)} units. "

    vehicle_details = []
    for vehicle, contribs in vehicle_data.items():
        total_segments = sum(c['segments'] for c in contribs)
        driver = contribs[0]['driver']
        region = contribs[0]['region']

        detail = f"<b>{vehicle} ({region})</b> accounted for {total_segments} of the {total} segments, "
        detail += f"all linked to <b>{driver}</b>"
        vehicle_details.append(detail)

    if vehicle_details:
        insights += vehicle_details[0]
        insights += ", indicating a likely oversight in logging into the ELD. "

        if len(vehicle_details) > 1:
            for detail in vehicle_details[1:]:
                insights += f"The remaining segments came from {detail}. "

    insights += "These findings suggest localized compliance lapses rather than systemic issues, "
    insights += "and reinforce the need for login adherence, especially for frequently used or reassigned vehicles."

    return insights


def generate_speeding_analysis_summary(
    behaviors_df: pd.DataFrame,
    safety_df: pd.DataFrame,
    trend_end_date: date,
) -> Dict:
    """Generate Driver Behavior & Speeding Analysis summary from both reports."""
    total_events = 0
    harsh_turn_count = 0
    speeding_by_region = {}

    # -------- Driver Behaviors Report ---------
    if not behaviors_df.empty:
        cols = _standardize_columns(behaviors_df)

        # Look for harsh turn column in behaviors
        for col in behaviors_df.columns:
            if 'harsh' in col.lower() and 'turn' in col.lower():
                harsh_turn_count += int(behaviors_df[col].sum())
                break

        # Look for speeding columns - these might be time strings
        heavy_col = None
        severe_col = None
        for col in behaviors_df.columns:
            col_lower = col.lower()
            if 'heavy' in col_lower and 'speed' in col_lower:
                heavy_col = col
            elif 'severe' in col_lower and 'speed' in col_lower:
                severe_col = col

        tags_col = cols.get('tags')
        if tags_col:
            region_mapping = {
                'great lakes': 'Great Lakes',
                'ohio valley': 'Ohio Valley',
                'southeast': 'Southeast',
                'gl': 'Great Lakes',
                'ov': 'Ohio Valley',
                'se': 'Southeast',
            }

            for region_key, region_name in region_mapping.items():
                mask = behaviors_df[tags_col].str.lower().str.contains(region_key, na=False)
                if mask.any():
                    region_df = behaviors_df[mask]
                    heavy_count = 0
                    severe_count = 0

                    if heavy_col and heavy_col in region_df.columns:
                        for val in region_df[heavy_col]:
                            if pd.notna(val) and str(val).strip() and str(val) != '0' and str(val) != '00:00:00':
                                heavy_count += 1

                    if severe_col and severe_col in region_df.columns:
                        for val in region_df[severe_col]:
                            if pd.notna(val) and str(val).strip() and str(val) != '0' and str(val) != '00:00:00':
                                severe_count += 1

                    speeding_by_region[region_name] = speeding_by_region.get(region_name, 0) + heavy_count + severe_count
                    total_events += heavy_count + severe_count

    # -------- Driver Safety Report ---------
    if not safety_df.empty:
        for col in safety_df.columns:
            if 'harsh' in col.lower() and 'turn' in col.lower():
                harsh_turn_count += int(safety_df[col].sum())

    return {
        'total_speeding_events': total_events,
        'harsh_turn_incidents': harsh_turn_count,
        'speeding_by_region': speeding_by_region,
    }


def generate_speeding_analysis_insights(summary_data: Dict) -> str:
    """Generate insights for Driver Behavior & Speeding Analysis."""
    total = summary_data.get('total_speeding_events', 0)
    harsh_turns = summary_data.get('harsh_turn_incidents', 0)
    by_region = summary_data.get('speeding_by_region', {})

    insights = f"A total of {total} high-risk speeding events were recorded this week, "
    insights += f"with {'no' if harsh_turns == 0 else harsh_turns} harsh turn incident{'s' if harsh_turns != 1 else ''} reported. "

    if by_region:
        # Sort regions by count
        sorted_regions = sorted(by_region.items(), key=lambda x: x[1], reverse=True)
        if sorted_regions:
            top_region = sorted_regions[0]
            insights += f"The {top_region[0]} region led with {top_region[1]} severe or heavy speeding events"

            if len(sorted_regions) > 1:
                other_regions = []
                for region, count in sorted_regions[1:3]:  # Next 2 regions
                    other_regions.append(f"{region} ({count})")
                insights += f", followed by {' and '.join(other_regions)}"

            insights += ". "

    if harsh_turns == 0:
        insights += "While the absence of harsh turns is encouraging, "

    insights += "the volume of heavy and severe speeding suggests a continued need for targeted coaching and stricter speed management across all regions."

    return insights


def generate_missed_dvir_summary(df: pd.DataFrame, trend_end_date: date) -> Dict:
    """Generate Missed DVIR summary statistics."""
    cols = _standardize_columns(df)

    # Find relevant columns
    driver_col = cols.get('driver')
    type_col = cols.get('type')

    if not driver_col:
        for col in df.columns:
            if 'driver' in col.lower():
                driver_col = col
                break

    total_missed = len(df)
    total_pre_trip = 0
    total_post_trip = 0

    # Count pre/post trips
    if type_col:
        for val in df[type_col]:
            val_lower = str(val).lower()
            if 'pre' in val_lower:
                total_pre_trip += 1
            elif 'post' in val_lower:
                total_post_trip += 1

    # Count by driver
    top_drivers = []
    if driver_col:
        driver_counts = df[driver_col].value_counts()

        for driver, total in driver_counts.head(15).items():
            driver_df = df[df[driver_col] == driver]
            pre_count = 0
            post_count = 0

            if type_col:
                for val in driver_df[type_col]:
                    val_lower = str(val).lower()
                    if 'pre' in val_lower:
                        pre_count += 1
                    elif 'post' in val_lower:
                        post_count += 1

            top_drivers.append({
                'driver': driver,
                'total': int(total),
                'pre_trip': pre_count,
                'post_trip': post_count
            })

    return {
        'total_missed': total_missed,
        'total_pre_trip': total_pre_trip,
        'total_post_trip': total_post_trip,
        'top_drivers': top_drivers
    }


def generate_missed_dvir_insights(summary_data: Dict) -> str:
    """Generate insights for Missed DVIRs."""
    total = summary_data.get('total_missed', 0)
    post_trips = summary_data.get('total_post_trip', 0)
    pre_trips = summary_data.get('total_pre_trip', 0)
    top_drivers = summary_data.get('top_drivers', [])

    insights = f"A total of {total} missed DVIRs were recorded this week, "
    insights += f"with {post_trips} post-trips and {pre_trips} pre-trips missed. "

    if top_drivers:
        # Get top 4 offenders
        top_4 = top_drivers[:4]
        driver_list = []
        for driver_data in top_4:
            driver_list.append(f"{driver_data['driver']} ({driver_data['total']})")

        insights += f"The most frequent offenders were {', '.join(driver_list[:-1])}, and {driver_list[-1]}. "

    insights += "Continued gaps in both start-of-day and end-of-day inspections highlight a need for renewed emphasis on driver accountability and routine DVIR training to ensure FMCSA compliance and fleet safety."

    return insights

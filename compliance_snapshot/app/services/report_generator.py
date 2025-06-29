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
    """Return summary statistics for Personal Conveyance usage."""
    cols = _standardize_columns(df)
    driver_col = cols.get("driver_name") or cols.get("driver")
    date_col = cols.get("date")
    pc_col = cols.get("pc_hours") or cols.get("personal_conveyance_duration")

    if not driver_col or not pc_col:
        raise ValueError("Driver name and PC duration columns are required")

    df2 = df.copy()
    df2[pc_col] = pd.to_numeric(df2[pc_col], errors="coerce").fillna(0.0)

    total_pc_time = float(df2[pc_col].sum())

    exceeded_daily_limit_count = 0
    drivers_with_3hrs = []

    if date_col:
        df2["date"] = pd.to_datetime(df2[date_col], errors="coerce")
        daily = df2.groupby([driver_col, df2["date"].dt.date])[pc_col].sum()
        exceeded_daily_limit_count = int((daily > 2).sum())
        over_three = daily.groupby(level=0).max()
        drivers_with_3hrs = [d for d, h in over_three.items() if h >= 3]
    else:
        totals = df2.groupby(driver_col)[pc_col].sum()
        drivers_with_3hrs = [d for d, h in totals.items() if h >= 3]

    totals = df2.groupby(driver_col)[pc_col].sum()
    drivers_list = [
        {"driver": drv, "hours": float(hours)}
        for drv, hours in totals.items()
        if drv in drivers_with_3hrs
    ]

    return {
        "total_pc_time": total_pc_time,
        "drivers_list": drivers_list,
        "exceeded_daily_limit_count": exceeded_daily_limit_count,
    }


def generate_pc_usage_insights(summary_data: Dict) -> str:
    """Generate insights for PC usage patterns using OpenAI with fallback."""
    try:
        if not os.environ.get("OPEN_API_KEY"):
            return generate_fallback_pc_usage_insights(summary_data)

        driver_lines = "\n".join(
            [f"   • {d['driver']}: {d['hours']:.2f} hrs" for d in summary_data.get("drivers_list", [])[:10]]
        )

        prompt = f"""Analyze this Personal Conveyance usage data in 2-3 sentences:

        Total PC Time: {summary_data['total_pc_time']:.2f} hours
        Drivers Exceeding Daily/Weekly Limit: {summary_data['exceeded_daily_limit_count']}

        Driver Totals:\n{driver_lines}

        Focus on compliance with the 2 hour/day and 14 hour/week limits."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERROR in generate_pc_usage_insights: {e}")
        return generate_fallback_pc_usage_insights(summary_data)


def generate_fallback_pc_usage_insights(summary_data: Dict) -> str:
    total = summary_data.get("total_pc_time", 0)
    exceed = summary_data.get("exceeded_daily_limit_count", 0)
    if exceed:
        return (
            f"Drivers exceeded PC limits on {exceed} occasions with a total of {total:.2f} hours used. "
            "Review PC policies with the drivers involved."
        )
    return f"Total PC usage was {total:.2f} hours with no limit violations detected."


def generate_unassigned_driving_summary(df: pd.DataFrame, trend_end_date: date) -> Dict:
    """Return summary statistics for Unassigned Driving segments."""
    cols = _standardize_columns(df)
    date_col = cols.get("date")
    region_col = cols.get("tags")
    seg_col = cols.get("unassigned_segments")
    time_col = cols.get("unassigned_hours")
    driver_col = cols.get("owner_of_the_time") or cols.get("driver_name") or cols.get("driver")
    vehicle_col = cols.get("vehicle")

    df2 = df.copy()
    if seg_col:
        df2[seg_col] = pd.to_numeric(df2[seg_col], errors="coerce").fillna(0)
    if time_col:
        df2[time_col] = pd.to_numeric(df2[time_col], errors="coerce").fillna(0.0)

    if date_col:
        df2["date"] = pd.to_datetime(df2[date_col], errors="coerce")
        current_start = pd.Timestamp(_monday_of(trend_end_date))
        prev_start = current_start - pd.Timedelta(weeks=1)
        current = df2[(df2["date"] >= current_start) & (df2["date"] <= current_start + pd.Timedelta(days=6))]
        previous = df2[(df2["date"] >= prev_start) & (df2["date"] < current_start)]
    else:
        current = df2
        previous = pd.DataFrame()

    total_current = int(current[seg_col].sum()) if seg_col else 0
    total_prev = int(previous[seg_col].sum()) if not previous.empty and seg_col else 0
    change = total_current - total_prev

    region_lookup = {
        "great lakes": "Great Lakes",
        "ohio valley": "Ohio Valley",
        "southeast": "Southeast",
    }

    by_region = {}
    if region_col:
        tags_lower = current[region_col].astype(str).str.lower()
        for key, name in region_lookup.items():
            mask = tags_lower.str.contains(key.replace(" ", "|"), na=False)
            seg_val = int(current.loc[mask, seg_col].sum()) if seg_col else 0
            time_val = float(current.loc[mask, time_col].sum()) if time_col else 0.0
            if seg_val or time_val:
                by_region[name] = {"segments": seg_val, "hours": time_val}

    top_contributors = []
    if driver_col and seg_col:
        counts = current.groupby(current[driver_col].astype(str))[seg_col].sum().sort_values(ascending=False)
        top_contributors = [{"driver": d, "segments": int(s)} for d, s in counts.head(5).items()]
    elif vehicle_col and seg_col:
        counts = current.groupby(current[vehicle_col].astype(str))[seg_col].sum().sort_values(ascending=False)
        top_contributors = [{"vehicle": v, "segments": int(s)} for v, s in counts.head(5).items()]

    chart = {region: data.get("hours", 0.0) for region, data in by_region.items()}

    return {
        "by_region": by_region,
        "total_current": total_current,
        "change": change,
        "top_contributors": top_contributors,
        "chart": chart,
    }


def generate_unassigned_driving_insights(summary_data: Dict) -> str:
    """Generate narrative insights for Unassigned Driving segments."""
    try:
        if not os.environ.get("OPEN_API_KEY"):
            return generate_fallback_unassigned_driving_insights(summary_data)

        region_lines = "\n".join(
            [f"   • {r}: {d['segments']} segments" for r, d in summary_data.get("by_region", {}).items()]
        )
        top_parts = []
        for item in summary_data.get("top_contributors", []):
            name = item.get("driver") or item.get("vehicle")
            segs = item.get("segments", 0)
            top_parts.append(f"**{name}** (**{segs}**)" )
        top_text = ", ".join(top_parts)

        prompt = f"""Provide a detailed paragraph about unassigned driving segments.

        Total Segments: {summary_data['total_current']} ({summary_data['change']:+})

        Regional Breakdown:\n{region_lines}

        Top Contributors: {top_text}

        Mention remediation strategies and week-over-week comparison."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERROR in generate_unassigned_driving_insights: {e}")
        return generate_fallback_unassigned_driving_insights(summary_data)


def generate_fallback_unassigned_driving_insights(summary_data: Dict) -> str:
    change = summary_data.get("change", 0)
    if change > 0:
        trend = f"rose by {change}"
    elif change < 0:
        trend = f"fell by {abs(change)}"
    else:
        trend = "remained stable"

    top = summary_data.get("top_contributors", [])
    names = ", ".join(
        item.get("driver") or item.get("vehicle") for item in top
    )
    return (
        f"Unassigned driving segments {trend} to {summary_data.get('total_current', 0)}. "
        f"Top contributors include {names}. Consider reinforcing login procedures."
    )


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


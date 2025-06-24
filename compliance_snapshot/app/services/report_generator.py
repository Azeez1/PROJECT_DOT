import os
from functools import lru_cache
from datetime import date
from typing import Dict

import pandas as pd
import openai

from .visualizations.chart_factory import normalize_violation_types

# Configure OpenAI via Replit environment variable
openai.api_key = os.environ.get("OPEN_API_KEY")


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

    return {
        "total_current": int(total_current),
        "total_previous": int(total_previous),
        "total_change": int(total_change),
        "by_region": by_region,
        "by_type": by_type,
    }


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


@lru_cache(maxsize=None)
def generate_summary_insights(summary_data: Dict) -> str:
    """Generate insights for weekly summary using OpenAI."""
    try:
        prompt = f"""
        Analyze this HOS violations data and provide 2-3 sentences of insights:
        
        Total Violations: {summary_data['total_current']} ({summary_data['total_change']:+})
        
        Regional Changes:
        {format_regional_data(summary_data.get('by_region', {}))}
        
        Top Violations:
        {format_violation_types(summary_data.get('by_type', {}))}
        
        Focus on:
        1. Overall trend (improving/worsening)
        2. Regional patterns
        3. Most concerning violation types
        4. Any positive developments
        
        Keep it concise and actionable.
        """
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return generate_fallback_summary_insights(summary_data)


def generate_fallback_summary_insights(summary_data: Dict) -> str:
    change = summary_data.get("total_change", 0)
    if change > 0:
        desc = f"Violations increased by {change}."
    elif change < 0:
        desc = f"Violations decreased by {abs(change)}."
    else:
        desc = "Violations were unchanged week over week."
    return desc


@lru_cache(maxsize=None)
def generate_trend_insights(trend_data: Dict) -> str:
    """Generate insights for 4-week trend using OpenAI."""
    try:
        prompt = f"""
        Analyze this 4-week HOS violation trend and provide 3-4 sentences of insights:
        
        Week-by-week data:
        {format_trend_data(trend_data)}
        
        Focus on:
        1. Overall trajectory of each violation type
        2. Which violations are improving vs worsening
        3. Any concerning patterns or positive trends
        4. Recommendations for areas needing attention
        
        Be specific about the data patterns and actionable in recommendations.
        """
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return generate_fallback_trend_insights(trend_data)


def generate_fallback_trend_insights(trend_data: Dict) -> str:
    return "Trend analysis not available."


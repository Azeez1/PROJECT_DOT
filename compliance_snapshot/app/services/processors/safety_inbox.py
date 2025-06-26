import pandas as pd
from pathlib import Path
from typing import Dict, Any


def process_safety_inbox(df: pd.DataFrame) -> pd.DataFrame:
    """Process Safety Inbox Report data with actual column structure."""
    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Check if this looks like a safety inbox report
    if 'event_type' not in df.columns or 'driver' not in df.columns:
        raise ValueError(
            "This doesn't appear to be a Safety Inbox Report - missing Event Type or Driver columns"
        )

    # Convert time column
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], errors='coerce')

    string_cols = [
        'vehicle', 'driver', 'driver_tags', 'event_type', 'status',
        'location', 'assigned_coach', 'device_tags', 'review_status'
    ]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace('nan', '')

    return df


def summarize(path: Path) -> Dict[str, Any]:
    """Summarize safety inbox report by aggregating events."""
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, engine="openpyxl")

    df = process_safety_inbox(df)

    total_events = len(df)

    events_by_type = {}
    if 'event_type' in df.columns:
        event_counts = df['event_type'].value_counts()
        events_by_type = event_counts.to_dict()

    events_by_status = {}
    if 'status' in df.columns:
        status_counts = df['status'].value_counts()
        events_by_status = status_counts.to_dict()

    events_by_review = {}
    if 'review_status' in df.columns:
        review_counts = df['review_status'].value_counts()
        events_by_review = review_counts.to_dict()

    top_drivers = {}
    if 'driver' in df.columns:
        driver_counts = df['driver'].value_counts().head(10)
        top_drivers = driver_counts.to_dict()

    events_by_region = {}
    if 'driver_tags' in df.columns:
        region_patterns = {
            'great lakes': ['great lakes', 'gl', 'great_lakes'],
            'ohio valley': ['ohio valley', 'ov', 'ohio_valley'],
            'southeast': ['southeast', 'se', 'south east'],
            'midwest': ['midwest', 'mw', 'mid west'],
            'corporate': ['corporate', 'corp']
        }
        for region, patterns in region_patterns.items():
            mask = df['driver_tags'].str.lower().str.contains('|'.join(patterns), na=False)
            count = mask.sum()
            if count > 0:
                events_by_region[region] = int(count)

    return {
        "total_events": total_events,
        "events_by_type": events_by_type,
        "events_by_status": events_by_status,
        "events_by_review": events_by_review,
        "top_drivers": top_drivers,
        "events_by_region": events_by_region,
    }

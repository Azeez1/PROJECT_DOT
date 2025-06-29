import pandas as pd
from pathlib import Path
from typing import Dict, Any


def convert_timedelta_to_string(td):
    """Convert timedelta to HH:MM:SS string format."""
    if pd.isna(td):
        return ''
    if isinstance(td, pd.Timedelta):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return str(td)


def parse_duration(duration_str: str) -> float:
    """Convert duration string (HH:MM:SS) to hours."""
    if pd.isna(duration_str) or str(duration_str).strip() == '':
        return 0.0

    duration_str = str(duration_str).strip()

    try:
        # Handle HH:MM:SS format
        if ':' in duration_str:
            parts = duration_str.split(':')
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours + minutes/60 + seconds/3600
            elif len(parts) == 2:
                hours = float(parts[0])
                minutes = float(parts[1])
                return hours + minutes/60
        # Handle decimal hours
        else:
            return float(duration_str)
    except:
        return 0.0


def process_driver_behaviors(df: pd.DataFrame) -> pd.DataFrame:
    """Process Safety Behavior Report data."""
    # Debug: Print original columns
    print(f"DEBUG Safety Behavior: Original columns: {list(df.columns)}")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for c in df.columns]

    print(f"DEBUG Safety Behavior: Normalized columns: {list(df.columns)}")

    # Convert any timedelta columns to string format
    time_columns = ['heavy_speeding_time_hh:mm:ss', 'severe_speeding_time_hh:mm:ss']
    # Also check for variations
    for col in df.columns:
        if 'speeding' in col and 'time' in col:
            if df[col].dtype == 'timedelta64[ns]':
                print(f"DEBUG: Converting timedelta column: {col}")
                df[col] = df[col].apply(convert_timedelta_to_string)

    # Handle any other timedelta columns
    for col in df.columns:
        if df[col].dtype == 'timedelta64[ns]':
            print(f"DEBUG: Converting additional timedelta column: {col}")
            df[col] = df[col].apply(convert_timedelta_to_string)

    # Check if this looks like a safety behavior report
    if not any('driver' in col for col in df.columns):
        raise ValueError(f"Missing driver column. Found columns: {list(df.columns)}")

    # Convert numeric columns
    numeric_cols = ['safety_score_rank', 'safety_score', 'harsh_turn_count', 'max_speed_mph']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Parse speeding times to hours
    heavy_col = None
    severe_col = None
    for col in df.columns:
        if 'heavy' in col and 'speeding' in col and 'time' in col:
            heavy_col = col
        elif 'severe' in col and 'speeding' in col and 'time' in col:
            severe_col = col

    if heavy_col:
        df['heavy_speeding_hours'] = df[heavy_col].apply(parse_duration)

    if severe_col:
        df['severe_speeding_hours'] = df[severe_col].apply(parse_duration)

    # Clean string columns
    string_cols = ['driver_name', 'tags', 'deactivation_status']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace('nan', '')

    return df


def summarize(path: Path) -> Dict[str, Any]:
    """Summarize safety behavior report."""
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, engine="openpyxl")

    df = process_driver_behaviors(df)

    # Total drivers
    total_drivers = len(df)

    # Average safety score
    avg_safety_score = 0
    if 'safety_score' in df.columns:
        avg_safety_score = float(df['safety_score'].mean())

    # Total harsh turns
    total_harsh_turns = 0
    if 'harsh_turn_count' in df.columns:
        total_harsh_turns = int(df['harsh_turn_count'].sum())

    # Total speeding time
    total_heavy_speeding = 0
    total_severe_speeding = 0
    if 'heavy_speeding_hours' in df.columns:
        total_heavy_speeding = float(df['heavy_speeding_hours'].sum())
    if 'severe_speeding_hours' in df.columns:
        total_severe_speeding = float(df['severe_speeding_hours'].sum())

    # Max speed across all drivers
    max_speed_overall = 0
    if 'max_speed_mph' in df.columns:
        max_speed_overall = float(df['max_speed_mph'].max())

    # Top 10 safest drivers (highest safety score)
    safest_drivers = []
    if 'driver_name' in df.columns and 'safety_score' in df.columns:
        top_safe = df.nlargest(10, 'safety_score')[['driver_name', 'safety_score']]
        safest_drivers = [
            {'driver': row['driver_name'], 'score': float(row['safety_score'])}
            for _, row in top_safe.iterrows()
        ]

    # Bottom 10 riskiest drivers (lowest safety score)
    riskiest_drivers = []
    if 'driver_name' in df.columns and 'safety_score' in df.columns:
        bottom_safe = df.nsmallest(10, 'safety_score')[['driver_name', 'safety_score']]
        riskiest_drivers = [
            {'driver': row['driver_name'], 'score': float(row['safety_score'])}
            for _, row in bottom_safe.iterrows()
        ]

    # Drivers with most harsh turns
    harsh_turn_drivers = []
    if 'driver_name' in df.columns and 'harsh_turn_count' in df.columns:
        top_harsh = df.nlargest(10, 'harsh_turn_count')[['driver_name', 'harsh_turn_count']]
        harsh_turn_drivers = [
            {'driver': row['driver_name'], 'count': int(row['harsh_turn_count'])}
            for _, row in top_harsh.iterrows()
        ]

    # Drivers with most speeding time
    speeding_drivers = []
    if all(col in df.columns for col in ['driver_name', 'heavy_speeding_hours', 'severe_speeding_hours']):
        df['total_speeding_hours'] = df['heavy_speeding_hours'] + df['severe_speeding_hours']
        top_speeding = df.nlargest(10, 'total_speeding_hours')[
            ['driver_name', 'heavy_speeding_hours', 'severe_speeding_hours', 'total_speeding_hours']
        ]
        speeding_drivers = [
            {
                'driver': row['driver_name'],
                'heavy_hours': float(row['heavy_speeding_hours']),
                'severe_hours': float(row['severe_speeding_hours']),
                'total_hours': float(row['total_speeding_hours'])
            }
            for _, row in top_speeding.iterrows()
        ]

    # By region (from tags)
    by_region = {}
    if 'tags' in df.columns:
        region_patterns = {
            'great lakes': ['great lakes', 'gl', 'great_lakes'],
            'ohio valley': ['ohio valley', 'ov', 'ohio_valley'],
            'southeast': ['southeast', 'se', 'south east'],
            'midwest': ['midwest', 'mw', 'mid west'],
            'corporate': ['corporate', 'corp']
        }

        for region, patterns in region_patterns.items():
            mask = df['tags'].str.lower().str.contains('|'.join(patterns), na=False)
            if mask.any():
                region_data = df[mask]
                by_region[region] = {
                    'driver_count': len(region_data),
                    'avg_safety_score': float(region_data['safety_score'].mean()) if 'safety_score' in region_data.columns else 0,
                    'total_harsh_turns': int(region_data['harsh_turn_count'].sum()) if 'harsh_turn_count' in region_data.columns else 0
                }

    # Deactivation status count
    deactivation_count = {}
    if 'deactivation_status' in df.columns:
        status_counts = df['deactivation_status'].value_counts()
        deactivation_count = status_counts.to_dict()

    return {
        "total_drivers": total_drivers,
        "avg_safety_score": avg_safety_score,
        "total_harsh_turns": total_harsh_turns,
        "total_heavy_speeding_hours": total_heavy_speeding,
        "total_severe_speeding_hours": total_severe_speeding,
        "max_speed_overall": max_speed_overall,
        "safest_drivers": safest_drivers,
        "riskiest_drivers": riskiest_drivers,
        "harsh_turn_drivers": harsh_turn_drivers,
        "speeding_drivers": speeding_drivers,
        "by_region": by_region,
        "deactivation_count": deactivation_count
    }

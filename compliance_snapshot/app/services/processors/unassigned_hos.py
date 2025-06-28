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
    """Convert duration string (HH:MM:SS or similar) to hours."""
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


def process_unassigned_hos(df: pd.DataFrame) -> pd.DataFrame:
    """Process Unassigned HOS Report data."""
    # Debug: Print original columns
    print(f"DEBUG Unassigned HOS: Original columns: {list(df.columns)}")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    print(f"DEBUG Unassigned HOS: Normalized columns: {list(df.columns)}")

    # Convert any timedelta columns to string format BEFORE any other processing
    for col in df.columns:
        if df[col].dtype == 'timedelta64[ns]':
            print(f"DEBUG: Converting timedelta column: {col}")
            df[col] = df[col].apply(convert_timedelta_to_string)

    # Expected columns
    expected_cols = [
        'date', 'vehicle', 'unassigned_time', 'unassigned_distance',
        'unassigned_segments', 'pending_segments', 'annotated_segments',
        'tags', 'owner_of_the_time'
    ]

    # Check if this looks like an unassigned HOS report
    if not any('unassigned' in col for col in df.columns):
        raise ValueError("This doesn't appear to be an Unassigned HOS Report")

    # Convert date column
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Parse unassigned time to hours
    time_col = None
    for col in df.columns:
        if 'unassigned' in col and 'time' in col:
            time_col = col
            break

    if time_col:
        df['unassigned_hours'] = df[time_col].apply(parse_duration)

    # Convert numeric columns
    numeric_cols = ['unassigned_distance', 'unassigned_segments', 'pending_segments', 'annotated_segments']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Clean string columns
    string_cols = ['vehicle', 'tags', 'owner_of_the_time']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace('nan', '')

    return df


def summarize(path: Path) -> Dict[str, Any]:
    """Summarize unassigned HOS report."""
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, engine="openpyxl")

    df = process_unassigned_hos(df)

    # Total unassigned time
    total_unassigned_hours = df['unassigned_hours'].sum() if 'unassigned_hours' in df.columns else 0

    # Total segments
    total_segments = 0
    if 'unassigned_segments' in df.columns:
        total_segments = int(df['unassigned_segments'].sum())

    # Pending segments
    pending_segments = 0
    if 'pending_segments' in df.columns:
        pending_segments = int(df['pending_segments'].sum())

    # Annotated segments
    annotated_segments = 0
    if 'annotated_segments' in df.columns:
        annotated_segments = int(df['annotated_segments'].sum())

    # By vehicle
    by_vehicle = {}
    if all(col in df.columns for col in ['vehicle', 'unassigned_hours', 'unassigned_segments']):
        vehicle_summary = df.groupby('vehicle').agg({
            'unassigned_hours': 'sum',
            'unassigned_segments': 'sum'
        })
        by_vehicle = {
            vehicle: {
                'hours': float(row['unassigned_hours']),
                'segments': int(row['unassigned_segments'])
            }
            for vehicle, row in vehicle_summary.iterrows()
        }

    # By owner
    by_owner = {}
    if 'owner_of_the_time' in df.columns and 'unassigned_hours' in df.columns:
        owner_totals = df.groupby('owner_of_the_time')['unassigned_hours'].sum()
        by_owner = {owner: float(hours) for owner, hours in owner_totals.items() if owner}

    # By region (from tags)
    by_region = {}
    if 'tags' in df.columns and 'unassigned_hours' in df.columns:
        region_patterns = {
            'great lakes': ['great lakes', 'gl', 'great_lakes'],
            'ohio valley': ['ohio valley', 'ov', 'ohio_valley'],
            'southeast': ['southeast', 'se', 'south east'],
            'midwest': ['midwest', 'mw', 'mid west'],
            'corporate': ['corporate', 'corp']
        }

        for region, patterns in region_patterns.items():
            mask = df['tags'].str.lower().str.contains('|'.join(patterns), na=False)
            total_hours = df.loc[mask, 'unassigned_hours'].sum()
            total_segs = df.loc[mask, 'unassigned_segments'].sum() if 'unassigned_segments' in df.columns else 0
            if total_hours > 0 or total_segs > 0:
                by_region[region] = {
                    'hours': float(total_hours),
                    'segments': int(total_segs)
                }

    # Top vehicles with most unassigned time
    top_vehicles = []
    if by_vehicle:
        sorted_vehicles = sorted(by_vehicle.items(), key=lambda x: x[1]['hours'], reverse=True)
        top_vehicles = [
            {
                'vehicle': vehicle,
                'hours': data['hours'],
                'segments': data['segments']
            }
            for vehicle, data in sorted_vehicles[:10]
        ]

    return {
        "total_unassigned_hours": float(total_unassigned_hours),
        "total_segments": total_segments,
        "pending_segments": pending_segments,
        "annotated_segments": annotated_segments,
        "by_vehicle": by_vehicle,
        "by_owner": by_owner,
        "by_region": by_region,
        "top_vehicles": top_vehicles,
        "total_vehicles": len(by_vehicle)
    }

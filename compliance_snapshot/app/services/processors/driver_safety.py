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


def process_drivers_safety(df: pd.DataFrame) -> pd.DataFrame:
    """Process Driver Safety Report data."""
    # Debug: Print original columns
    print(f"DEBUG Driver Safety: Original columns: {list(df.columns)}")
    print(f"DEBUG Driver Safety: Column count: {len(df.columns)}")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for c in df.columns]

    print(f"DEBUG Driver Safety: Normalized columns: {list(df.columns)}")

    # Handle datetime/timedelta columns
    time_columns = ['start_time', 'end_time']
    for col in time_columns:
        if col in df.columns:
            if df[col].dtype == 'timedelta64[ns]':
                print(f"DEBUG: Converting timedelta column: {col}")
                df[col] = df[col].apply(convert_timedelta_to_string)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].astype(str)

    # Handle duration column (might be in minutes)
    if 'duration_min' in df.columns:
        if df['duration_min'].dtype == 'timedelta64[ns]':
            df['duration_min'] = df['duration_min'].dt.total_seconds() / 60
        else:
            df['duration_min'] = pd.to_numeric(df['duration_min'], errors='coerce').fillna(0)

    # Check for any other timedelta columns
    for col in df.columns:
        if df[col].dtype == 'timedelta64[ns]':
            print(f"DEBUG: Converting additional timedelta column: {col}")
            df[col] = df[col].apply(convert_timedelta_to_string)

    # Safety event columns (these are typically counts or booleans)
    safety_events = [
        'harsh_accel', 'harsh_brake', 'harsh_turn', 'mobile_usage',
        'inattentive_driving', 'drowsy', 'rolling_stop',
        'did_not_yield_manual', 'ran_red_light_manual',
        'lane_departure_manual', 'obstructed_camera_automatic',
        'obstructed_camera_manual', 'eating/drinking_manual',
        'smoking_manual', 'no_seat_belt', 'forward_collision_warning'
    ]

    # Convert safety event columns to numeric (0 or 1)
    for col in safety_events:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.lower().isin(['yes', 'true', '1', 1]).astype(int)
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Convert distance to numeric
    if 'distance_mi' in df.columns:
        df['distance_mi'] = pd.to_numeric(df['distance_mi'], errors='coerce').fillna(0)

    # Clean ID columns
    id_cols = ['trip_id', 'vehicle_id', 'driver_id']
    for col in id_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


def summarize(path: Path) -> Dict[str, Any]:
    """Summarize driver safety report."""
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, engine="openpyxl")

    df = process_drivers_safety(df)

    total_trips = len(df)

    total_distance = 0
    total_duration = 0
    if 'distance_mi' in df.columns:
        total_distance = float(df['distance_mi'].sum())
    if 'duration_min' in df.columns:
        total_duration = float(df['duration_min'].sum())

    safety_events = [
        'harsh_accel', 'harsh_brake', 'harsh_turn', 'mobile_usage',
        'inattentive_driving', 'drowsy', 'rolling_stop',
        'did_not_yield_manual', 'ran_red_light_manual',
        'lane_departure_manual', 'obstructed_camera_automatic',
        'obstructed_camera_manual', 'eating/drinking_manual',
        'smoking_manual', 'no_seat_belt', 'forward_collision_warning'
    ]

    event_counts = {}
    for event in safety_events:
        if event in df.columns:
            count = int(df[event].sum())
            if count > 0:
                readable_name = event.replace('_', ' ').replace('/', '/').title()
                event_counts[readable_name] = count

    violation_columns = [col for col in safety_events if col in df.columns]
    if 'driver_id' in df.columns and violation_columns:
        df['total_violations'] = df[violation_columns].sum(axis=1)

        driver_violations = df.groupby('driver_id').agg({
            'total_violations': 'sum',
            'trip_id': 'count'
        }).rename(columns={'trip_id': 'trip_count'})

        top_violators = driver_violations.nlargest(10, 'total_violations')
        worst_drivers = [
            {
                'driver': driver,
                'violations': int(row['total_violations']),
                'trips': int(row['trip_count']),
                'violations_per_trip': round(row['total_violations'] / row['trip_count'], 2) if row['trip_count'] > 0 else 0
            }
            for driver, row in top_violators.iterrows()
        ]
    else:
        worst_drivers = []

    most_common_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    vehicle_incidents = []
    if 'vehicle_id' in df.columns and violation_columns:
        vehicle_violations = df.groupby('vehicle_id')['total_violations'].sum()
        top_vehicles = vehicle_violations.nlargest(10)
        vehicle_incidents = [
            {'vehicle': vehicle, 'violations': int(count)}
            for vehicle, count in top_vehicles.items()
        ]

    total_violations = sum(event_counts.values())
    safety_score = max(0, 100 - (total_violations / total_trips * 10)) if total_trips > 0 else 100

    safe_trips = 0
    if 'total_violations' in df.columns:
        safe_trips = int((df['total_violations'] == 0).sum())

    return {
        "total_trips": total_trips,
        "total_distance": total_distance,
        "total_duration_minutes": total_duration,
        "total_duration_hours": round(total_duration / 60, 2),
        "event_counts": event_counts,
        "total_violations": total_violations,
        "worst_drivers": worst_drivers,
        "most_common_events": most_common_events,
        "vehicle_incidents": vehicle_incidents,
        "fleet_safety_score": round(safety_score, 1),
        "safe_trips": safe_trips,
        "safe_trip_percentage": round(safe_trips / total_trips * 100, 1) if total_trips > 0 else 0,
        "violations_per_trip": round(total_violations / total_trips, 2) if total_trips > 0 else 0
    }

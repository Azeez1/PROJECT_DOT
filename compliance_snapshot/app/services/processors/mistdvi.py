import pandas as pd
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta


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


def process_mistdvi(df: pd.DataFrame) -> pd.DataFrame:
    """Process Missed DVIR Report data."""
    # Debug: Print original columns
    print(f"DEBUG Missed DVIR: Original columns: {list(df.columns)}")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    print(f"DEBUG Missed DVIR: Normalized columns: {list(df.columns)}")

    # Handle datetime columns - they might be datetime or timedelta
    time_columns = ['start_time', 'end_time']
    for col in time_columns:
        if col in df.columns:
            if df[col].dtype == 'timedelta64[ns]':
                print(f"DEBUG: Converting timedelta column: {col}")
                df[col] = df[col].apply(convert_timedelta_to_string)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                # Keep datetime as is, SQLite can handle it as string
                df[col] = df[col].astype(str)

    # Also check for any other timedelta columns
    for col in df.columns:
        if col not in time_columns and df[col].dtype == 'timedelta64[ns]':
            print(f"DEBUG: Converting additional timedelta column: {col}")
            df[col] = df[col].apply(convert_timedelta_to_string)

    # Expected columns
    expected_cols = ['vehicle', 'driver', 'start_time', 'end_time', 'type']

    # Check if this looks like a Missed DVIR report
    if not all(col in df.columns for col in ['vehicle', 'driver']):
        # Check if we at least have some key columns
        if not any(col in df.columns for col in ['vehicle', 'driver', 'dvir', 'type']):
            raise ValueError(f"Missing required columns for Missed DVIR report. Found: {list(df.columns)}")

    # Clean string columns
    string_cols = ['vehicle', 'driver', 'type']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace('nan', '')

    # Calculate duration if we have both start and end times
    if 'start_time' in df.columns and 'end_time' in df.columns:
        try:
            # Try to parse times and calculate duration
            start_times = pd.to_datetime(df['start_time'], errors='coerce')
            end_times = pd.to_datetime(df['end_time'], errors='coerce')

            # Calculate duration in hours
            df['duration_hours'] = (end_times - start_times).dt.total_seconds() / 3600
            df['duration_hours'] = df['duration_hours'].fillna(0)
        except:
            df['duration_hours'] = 0

    return df


def summarize(path: Path) -> Dict[str, Any]:
    """Summarize Missed DVIR report."""
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, engine="openpyxl")

    df = process_mistdvi(df)

    # Total missed DVIRs
    total_missed = len(df)

    # By type
    by_type = {}
    if 'type' in df.columns:
        type_counts = df['type'].value_counts()
        by_type = type_counts.to_dict()

    # By driver
    by_driver = {}
    if 'driver' in df.columns:
        driver_counts = df['driver'].value_counts()
        by_driver = driver_counts.to_dict()

    # By vehicle
    by_vehicle = {}
    if 'vehicle' in df.columns:
        vehicle_counts = df['vehicle'].value_counts()
        by_vehicle = vehicle_counts.to_dict()

    # Top drivers with most missed DVIRs
    top_drivers = []
    if by_driver:
        sorted_drivers = sorted(by_driver.items(), key=lambda x: x[1], reverse=True)
        top_drivers = [
            {'driver': driver, 'count': count}
            for driver, count in sorted_drivers[:10]
        ]

    # Top vehicles with most missed DVIRs
    top_vehicles = []
    if by_vehicle:
        sorted_vehicles = sorted(by_vehicle.items(), key=lambda x: x[1], reverse=True)
        top_vehicles = [
            {'vehicle': vehicle, 'count': count}
            for vehicle, count in sorted_vehicles[:10]
        ]

    # Pre/Post trip breakdown if type contains this info
    pre_trip_count = 0
    post_trip_count = 0
    if 'type' in df.columns:
        type_lower = df['type'].str.lower()
        pre_trip_count = type_lower.str.contains('pre', na=False).sum()
        post_trip_count = type_lower.str.contains('post', na=False).sum()

    # Average duration if calculated
    avg_duration = 0
    if 'duration_hours' in df.columns:
        avg_duration = float(df['duration_hours'].mean())

    return {
        "total_missed_dvirs": total_missed,
        "by_type": by_type,
        "by_driver": by_driver,
        "by_vehicle": by_vehicle,
        "top_drivers": top_drivers,
        "top_vehicles": top_vehicles,
        "pre_trip_count": int(pre_trip_count),
        "post_trip_count": int(post_trip_count),
        "average_duration_hours": avg_duration,
        "total_drivers": len(by_driver),
        "total_vehicles": len(by_vehicle)
    }

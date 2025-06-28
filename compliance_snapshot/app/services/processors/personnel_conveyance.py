import pandas as pd
from pathlib import Path
from typing import Dict, Any
from datetime import timedelta


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


def process_personnel_conveyance(df: pd.DataFrame) -> pd.DataFrame:
    """Process Personnel Conveyance Report data."""
    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for c in df.columns]

    # Convert timedelta objects to string format HH:MM:SS
    for col in df.columns:
        if df[col].dtype == 'timedelta64[ns]':
            # Convert timedelta to string in HH:MM:SS format
            df[col] = df[col].apply(lambda x: str(x).split(' ')[-1] if pd.notna(x) else '')

    # Also specifically check the duration column
    duration_col = None
    for col in df.columns:
        if 'duration' in col and 'personal' in col:
            duration_col = col
            break

    if duration_col and df[duration_col].dtype == 'timedelta64[ns]':
        df[duration_col] = df[duration_col].apply(lambda x: str(x).split(' ')[-1] if pd.notna(x) else '')

    # Expected columns
    expected_cols = [
        'date', 'driver_name', 'eld_exempt', 'eld_exempt_reason',
        'personal_conveyance_duration', 'tags', 'comments'
    ]

    # Check if this looks like a personnel conveyance report
    if 'driver_name' not in df.columns or 'personal_conveyance_duration' not in df.columns:
        raise ValueError("Missing required columns for Personnel Conveyance report")

    # Convert date column
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Parse duration to hours
    if 'personal_conveyance_duration' in df.columns:
        df['pc_hours'] = df['personal_conveyance_duration'].apply(parse_duration)
        df['pc_hours'] = df['pc_hours'].apply(
            lambda x: int(x) if pd.notna(x) and float(x).is_integer() else x
        )

    # Clean string columns
    string_cols = ['driver_name', 'eld_exempt', 'eld_exempt_reason', 'tags', 'comments']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace('nan', '')

    return df


def summarize(path: Path) -> Dict[str, Any]:
    """Summarize personnel conveyance report."""
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path, engine="openpyxl")

    df = process_personnel_conveyance(df)

    # Total PC time
    total_pc_hours = df['pc_hours'].sum() if 'pc_hours' in df.columns else 0

    # PC time by driver
    pc_by_driver = {}
    if 'driver_name' in df.columns and 'pc_hours' in df.columns:
        driver_totals = df.groupby('driver_name')['pc_hours'].sum()
        pc_by_driver = driver_totals.to_dict()

    # Drivers exceeding 2 hours in a single day
    drivers_over_2hrs = []
    if all(col in df.columns for col in ['driver_name', 'date', 'pc_hours']):
        daily_totals = df.groupby(['driver_name', df['date'].dt.date])['pc_hours'].sum()
        over_2hrs = daily_totals[daily_totals > 2.0]
        drivers_over_2hrs = [
            {
                'driver': driver,
                'date': str(date),
                'hours': float(hours)
            }
            for (driver, date), hours in over_2hrs.items()
        ]

    # Count of ELD exempt entries
    eld_exempt_count = 0
    if 'eld_exempt' in df.columns:
        eld_exempt_count = df['eld_exempt'].str.lower().isin(['yes', 'true', '1']).sum()

    # PC usage by region (from tags)
    pc_by_region = {}
    if 'tags' in df.columns and 'pc_hours' in df.columns:
        region_patterns = {
            'great lakes': ['great lakes', 'gl', 'great_lakes'],
            'ohio valley': ['ohio valley', 'ov', 'ohio_valley'],
            'southeast': ['southeast', 'se', 'south east'],
            'midwest': ['midwest', 'mw', 'mid west'],
            'corporate': ['corporate', 'corp']
        }

        for region, patterns in region_patterns.items():
            mask = df['tags'].str.lower().str.contains('|'.join(patterns), na=False)
            total_hours = df.loc[mask, 'pc_hours'].sum()
            if total_hours > 0:
                pc_by_region[region] = float(total_hours)

    return {
        "total_pc_hours": float(total_pc_hours),
        "pc_by_driver": pc_by_driver,
        "drivers_over_2hrs_daily": drivers_over_2hrs,
        "eld_exempt_count": int(eld_exempt_count),
        "pc_by_region": pc_by_region,
        "total_drivers": len(pc_by_driver)
    }

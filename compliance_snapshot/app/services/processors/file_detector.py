import pandas as pd
from pathlib import Path
from typing import Optional, Tuple


def detect_report_type(filepath: Path) -> Tuple[Optional[str], pd.DataFrame]:
    """Detect the report type from file content."""
    if filepath.suffix.lower() == '.csv':
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath, engine='openpyxl')

    cols_lower = [c.lower().strip() for c in df.columns]

    if any('violation type' in col for col in cols_lower):
        return 'hos', df
    elif any('event type' in col for col in cols_lower) and any('driver' in col for col in cols_lower):
        safety_cols = ['vehicle', 'status', 'review_status', 'event_url']
        if any(any(s in col for col in cols_lower) for s in safety_cols):
            return 'safety_inbox', df
    elif any('personal conveyance' in col or 'pc_duration' in col for col in cols_lower):
        return 'personnel_conveyance', df
    elif any('unassigned' in col and 'segments' in col for col in cols_lower):
        return 'unassigned_hos', df
    elif any('mistdvi' in col or 'missed dvir' in col for col in cols_lower):
        return 'mistdvi', df
    elif any('driver' in col and 'behavior' in col for col in cols_lower):
        return 'driver_behaviors', df
    elif any('driver' in col and 'safety' in col and 'score' in col for col in cols_lower):
        return 'drivers_safety', df

    filename_lower = filepath.stem.lower()
    if 'hos' in filename_lower and 'violation' in filename_lower:
        return 'hos', df
    elif 'safety' in filename_lower and 'inbox' in filename_lower:
        return 'safety_inbox', df

    return 'hos', df

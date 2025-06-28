import logging
import re
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SAFETY_INBOX_COLUMNS = [
    "Time",
    "Vehicle",
    "Driver",
    "Driver Tags",
    "Event Type",
    "Status",
    "Location",
    "Event URL",
    "Assigned Coach",
    "Device Tags",
    "Review Status",
]

def _norm(col: str) -> str:
    """Normalize column name for comparison."""
    return re.sub(r"[_\s]+", " ", col).strip().lower()


def detect_report_type(filepath: Path) -> Tuple[Optional[str], pd.DataFrame]:
    """Detect the report type from file content."""
    if filepath.suffix.lower() == '.csv':
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath, engine='openpyxl')

    cols_norm = [_norm(c) for c in df.columns]
    logger.debug("Found columns: %s", cols_norm)
    expected_norm = {_norm(c) for c in SAFETY_INBOX_COLUMNS}
    logger.debug("Expected Safety Inbox columns: %s", sorted(expected_norm))
    missing = sorted(expected_norm - set(cols_norm))
    logger.debug("Missing Safety Inbox columns: %s", missing)

    if any('violation type' in col for col in cols_norm):
        return 'hos', df
    elif expected_norm <= set(cols_norm):
        return 'safety_inbox', df
    elif any('event type' in col for col in cols_norm) and any('driver' in col for col in cols_norm):
        safety_cols = ['vehicle', 'status', 'review status', 'event url']
        if any(any(s in col for col in cols_norm) for s in safety_cols):
            return 'safety_inbox', df
    elif any('personal conveyance' in col for col in cols_norm):
        # Check for the duration column with parentheses
        if any('personal conveyance (duration)' in col or 'personal conveyance duration' in col for col in cols_norm):
            return 'personnel_conveyance', df
        # Also check for driver name and date as additional validation
        elif any('driver name' in col for col in cols_norm) and any('date' in col for col in cols_norm):
            return 'personnel_conveyance', df
    elif any('pc_duration' in col for col in cols_norm):
        return 'personnel_conveyance', df
    elif any('unassigned' in col and ('time' in col or 'segments' in col) for col in cols_norm):
        # Additional check for vehicle column
        if any('vehicle' in col for col in cols_norm):
            return 'unassigned_hos', df
        # Still return unassigned_hos if we have strong indicators
        elif any('unassigned segments' in col or 'unassigned time' in col for col in cols_norm):
            return 'unassigned_hos', df
    elif any('mistdvi' in col or 'missed dvir' in col or 'dvir' in col for col in cols_norm):
        return 'mistdvi', df
    elif all(col in cols_norm for col in ['vehicle', 'driver', 'start time', 'end time', 'type']):
        # If we have all these specific columns, it's likely a Missed DVIR report
        return 'mistdvi', df
    elif any('driver' in col and 'behavior' in col for col in cols_norm):
        return 'driver_behaviors', df
    elif any('driver' in col and 'safety' in col and 'score' in col for col in cols_norm):
        return 'drivers_safety', df

    filename_lower = filepath.stem.lower()
    if 'hos' in filename_lower and 'violation' in filename_lower:
        return 'hos', df
    elif 'safety' in filename_lower and 'inbox' in filename_lower:
        return 'safety_inbox', df
    elif 'mistdvi' in filename_lower or 'missed dvir' in filename_lower or ('dvir' in filename_lower and 'miss' in filename_lower):
        return 'mistdvi', df
    # Fallback detection for Unassigned HOS based on filename
    if 'unassigned' in filename_lower and ('hos' in filename_lower or 'hours' in filename_lower):
        return 'unassigned_hos', df

    return 'hos', df

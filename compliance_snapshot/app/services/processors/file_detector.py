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

    # User-requested debug output
    print(f"DEBUG: Checking file {filepath.name}")
    print(f"DEBUG: First 5 columns: {df.columns.tolist()[:5]}")

    report_type: Optional[str] = None

    if any('violation type' in col for col in cols_norm):
        report_type = 'hos'
    elif expected_norm <= set(cols_norm):
        report_type = 'safety_inbox'
    elif any('event type' in col for col in cols_norm) and any('driver' in col for col in cols_norm):
        safety_cols = ['vehicle', 'status', 'review status', 'event url']
        if any(any(s in col for col in cols_norm) for s in safety_cols):
            report_type = 'safety_inbox'
    elif any('personal conveyance' in col for col in cols_norm):
        if any('personal conveyance (duration)' in col or 'personal conveyance duration' in col for col in cols_norm):
            report_type = 'personnel_conveyance'
        elif any('driver name' in col for col in cols_norm) and any('date' in col for col in cols_norm):
            report_type = 'personnel_conveyance'
    elif any('pc_duration' in col for col in cols_norm):
        report_type = 'personnel_conveyance'
    elif any('unassigned' in col and ('time' in col or 'segments' in col) for col in cols_norm):
        # Additional check for vehicle column
        if any('vehicle' in col for col in cols_norm):
            report_type = 'unassigned_hos'
        elif any('unassigned segments' in col or 'unassigned time' in col for col in cols_norm):
            report_type = 'unassigned_hos'
    elif any('mistdvi' in col or 'missed dvir' in col or 'dvir' in col for col in cols_norm):
        report_type = 'mistdvi'
    elif all(col in cols_norm for col in ['vehicle', 'driver', 'start time', 'end time', 'type']):
        # If we have all these specific columns, it's likely a Missed DVIR report
        report_type = 'mistdvi'
    elif any('driver' in col and 'behavior' in col for col in cols_norm):
        report_type = 'driver_behaviors'
    elif any('safety score' in col for col in cols_norm) and any('driver name' in col for col in cols_norm):
        # If we have safety score and driver name, it's likely a safety behavior report
        report_type = 'driver_behaviors'
    elif any('harsh turn' in col for col in cols_norm) or any('speeding time' in col for col in cols_norm):
        # Additional indicators for safety behavior report
        if any('driver' in col for col in cols_norm):
            report_type = 'driver_behaviors'
    elif any('driver' in col and 'safety' in col and 'score' in col for col in cols_norm):
        report_type = 'driver_safety'
    elif any('trip id' in col or 'trip_id' in col for col in cols_norm):
        if any('vehicle' in col for col in cols_norm) and any('driver' in col for col in cols_norm):
            return 'driver_safety', df
    elif any('trip id' in col or 'trip_id' in col for col in cols_norm) and any('driver id' in col or 'driver_id' in col for col in cols_norm):
        if any('harsh' in col or 'collision' in col or 'seat belt' in col for col in cols_norm):
            return 'driver_safety', df
    elif any('harsh accel' in col or 'harsh brake' in col or 'harsh turn' in col for col in cols_norm):
        report_type = 'driver_safety'
    elif sum(1 for col in cols_norm if any(event in col for event in ['harsh accel', 'harsh brake', 'harsh turn', 'mobile usage', 'drowsy', 'seat belt'])) >= 3:
        return 'driver_safety', df

    filename_lower = filepath.stem.lower()
    if 'hos' in filename_lower and 'violation' in filename_lower:
        report_type = report_type or 'hos'
    elif 'safety' in filename_lower and 'inbox' in filename_lower:
        report_type = report_type or 'safety_inbox'
    elif 'mistdvi' in filename_lower or 'missed dvir' in filename_lower or ('dvir' in filename_lower and 'miss' in filename_lower):
        report_type = report_type or 'mistdvi'
    elif 'safety behavior' in filename_lower or 'driver behavior' in filename_lower:
        return 'driver_behaviors', df
    elif 'driver safety' in filename_lower and 'behavior' not in filename_lower:
        return 'driver_safety', df
    if 'unassigned' in filename_lower and ('hos' in filename_lower or 'hours' in filename_lower):
        report_type = report_type or 'unassigned_hos'

    if not report_type:
        report_type = 'hos'

    print(f"DEBUG: File {filepath.name} detected as: {report_type}")
    return report_type, df

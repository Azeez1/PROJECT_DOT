import pandas as pd
from pathlib import Path as _P
import sys

ROOT = _P(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.processors.file_detector import detect_report_type


def test_detect_safety_inbox(tmp_path):
    cols = [
        ' Time ',
        'VEHICLE',
        'Driver',
        'Driver Tags ',
        'event type',
        'Status',
        'Location',
        'Event URL',
        'Assigned Coach',
        'Device Tags',
        'Review Status',
    ]
    df = pd.DataFrame([], columns=cols)
    path = tmp_path / "safety.csv"
    df.to_csv(path, index=False)

    report, _ = detect_report_type(path)
    assert report == 'safety_inbox'

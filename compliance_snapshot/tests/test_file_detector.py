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


def test_detect_personnel_conveyance(tmp_path):
    cols = [
        'Date',
        'Driver Name',
        'ELD Exempt',
        'ELD Exempt Reason',
        'Personal Conveyance (Duration)',
        'Tags',
        'Comments',
    ]
    df = pd.DataFrame([], columns=cols)
    path = tmp_path / 'pc.csv'
    df.to_csv(path, index=False)

    report, _ = detect_report_type(path)
    assert report == 'personnel_conveyance'


def test_detect_unassigned_hos(tmp_path):
    cols = [
        'DATE',
        'Vehicle',
        'Unassigned Time',
        'Unassigned Distance',
        'Unassigned Segments',
        'Pending Segments',
        'Annotated Segments',
        'Tags',
        'Owner of the Time'
    ]
    df = pd.DataFrame([], columns=cols)
    path = tmp_path / 'unassigned.csv'
    df.to_csv(path, index=False)

    report, _ = detect_report_type(path)
    assert report == 'unassigned_hos'


def test_detect_mistdvi_by_cols(tmp_path):
    cols = [
        'Vehicle',
        'Driver',
        'Start Time',
        'End Time',
        'Type'
    ]
    df = pd.DataFrame([], columns=cols)
    path = tmp_path / 'mistdvi.csv'
    df.to_csv(path, index=False)

    report, _ = detect_report_type(path)
    assert report == 'mistdvi'


def test_detect_mistdvi_by_filename(tmp_path):
    df = pd.DataFrame([], columns=['A', 'B'])
    path = tmp_path / 'missed_dvir_report.csv'
    df.to_csv(path, index=False)

    report, _ = detect_report_type(path)
    assert report == 'mistdvi'

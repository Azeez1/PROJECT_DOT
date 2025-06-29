import pandas as pd
from pathlib import Path as _P
import sys
ROOT = _P(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.processors.personnel_conveyance import process_personnel_conveyance


def test_process_personnel_conveyance_columns():
    df = pd.DataFrame(
        {
            "DRIVERS": ["A", "B"],
            "Sum of Personal Conveyance (Duration)": ["01:00:00", "02:30:00"],
        }
    )
    result = process_personnel_conveyance(df)
    assert "driver_name" in result.columns
    assert "pc_hours" in result.columns
    assert result.loc[0, "pc_hours"] == 1.0
    assert result.loc[1, "pc_hours"] == 2.5

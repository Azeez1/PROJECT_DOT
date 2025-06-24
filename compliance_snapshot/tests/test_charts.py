import pandas as pd
from datetime import date, timedelta
from pathlib import Path
import sys
from pathlib import Path as _P

ROOT = _P(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.visualizations.chart_factory import make_stacked_bar, make_trend_line

def test_make_stacked_bar(tmp_path):
    df = pd.DataFrame({
        "Tags": ["OV", "GL", "MW", "SE", "OV GL", "XX"],
        "Violation Type": ["A", "B", "A", "B", "A", "B"],
    })
    out = tmp_path / "bar.png"
    result = make_stacked_bar(df, out)
    assert result == out
    assert out.exists()

def test_make_trend_line(tmp_path):
    start = date(2025, 5, 1)
    records = []
    for i in range(30):
        records.append({"Week": start + timedelta(days=i), "Violation Type": "A"})
    df = pd.DataFrame(records)

    out = tmp_path / "trend.png"
    result = make_trend_line(df, start + timedelta(days=28), out)
    assert result == out
    assert out.exists()

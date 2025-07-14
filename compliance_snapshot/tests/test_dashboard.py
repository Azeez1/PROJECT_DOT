import os
import sqlite3
import pandas as pd
from pathlib import Path as _P
import sys

ROOT = _P(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

os.environ.setdefault("OPEN_API_KEY", "test")
from app.main import app

import uuid


def _create_db(tmp_path: _P) -> str:
    ticket = uuid.uuid4().hex
    ticket_path = _P(f"/tmp/{ticket}")
    ticket_path.mkdir(parents=True, exist_ok=True)
    db_path = ticket_path / "snapshot.db"
    con = sqlite3.connect(db_path)

    pd.DataFrame({"driver_name": ["A", "B", "A"]}).to_sql(
        "personnel_conveyance", con, index=False
    )
    pd.DataFrame({"vehicle": ["V1", "V2", "V1"]}).to_sql(
        "unassigned_hos", con, index=False
    )
    pd.DataFrame({"type": ["pre", "post", "pre"]}).to_sql("mistdvi", con, index=False)
    pd.DataFrame({"driver_name": ["A", "B", "A"]}).to_sql(
        "driver_behaviors", con, index=False
    )
    pd.DataFrame({"driver_id": ["D1", "D2", "D1"]}).to_sql(
        "driver_safety", con, index=False
    )
    con.close()
    return ticket

def test_dashboard_data_keys(tmp_path):
    ticket = _create_db(tmp_path)
    client = TestClient(app)
    resp = client.get(f"/api/{ticket}/dashboard-data")
    assert resp.status_code == 200
    data = resp.json()
    expected = {
        "personnel_conveyance",
        "unassigned_hos",
        "mistdvi",
        "driver_behaviors",
        "driver_safety",
    }
    assert expected.issubset(data.keys())
    for key in expected:
        assert set(data[key].keys()) == {"type", "data", "title"}

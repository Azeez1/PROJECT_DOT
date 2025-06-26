import os
import pandas as pd
from pathlib import Path as _P
import sys

ROOT = _P(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

os.environ.setdefault("OPEN_API_KEY", "test")
from app.main import app


def test_upload_safety_inbox(tmp_path):
    cols = [
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
    df = pd.DataFrame([], columns=cols)
    path = tmp_path / "safety_inbox.csv"
    df.to_csv(path, index=False)

    client = TestClient(app)
    with path.open("rb") as fh:
        resp = client.post(
            "/generate",
            files={"files": ("safety_inbox.csv", fh, "text/csv")},
            allow_redirects=False,
        )
    assert resp.status_code == 303
    loc = resp.headers["location"]
    assert loc.startswith("/wizard/")
    ticket = loc.split("/")[-1]

    tables_resp = client.get(f"/api/{ticket}/tables")
    assert tables_resp.status_code == 200
    tables = tables_resp.json()
    assert tables == ["safety_inbox"]

    wizard_resp = client.get(f"/wizard/{ticket}")
    assert wizard_resp.status_code == 200

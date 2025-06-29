from pathlib import Path
from fastapi import UploadFile, Response
import pandas as pd
import datetime

async def save_uploads(folder: Path, files: list[UploadFile]):
    """Save uploaded files to disk without loading into memory."""
    for f in files:
        # Skip empty file inputs (browsers submit an UploadFile with an empty
        # filename when the user leaves a file field blank).
        if not f.filename:
            continue

        # Ensure the filename does not contain directories from the client.
        dest = folder / Path(f.filename).name

        with dest.open("wb") as out:
            while True:
                chunk = await f.read(1024 * 1024)  # 1 MB
                if not chunk:
                    break
                out.write(chunk)


def _hms(val: object) -> str:
    """Return HH:MM:SS string for timedelta-like values."""
    if pd.isna(val):
        return ""
    try:
        td = pd.to_timedelta(val)
    except Exception:
        s = str(val)
        if ":" in s:
            s = s.split(" ")[-1].split(".")[0]
        return s
    total = int(td.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def sanitize_for_sql(df: pd.DataFrame) -> pd.DataFrame:
    """Convert ``timedelta`` or duration columns to HH:MM:SS strings."""
    for col in df.columns:
        if pd.api.types.is_timedelta64_dtype(df[col]) or "duration" in col.lower():
            df[col] = df[col].apply(_hms)
        elif df[col].dtype == object and df[col].map(
            lambda x: isinstance(x, datetime.timedelta)
        ).any():
            df[col] = df[col].apply(lambda x: _hms(x) if isinstance(x, datetime.timedelta) else x)
    return df


def file_response(path: Path, *, filename: str, media_type: str = "application/octet-stream") -> Response:
    """Return a ``Response`` with the contents of ``path``.

    ``FileResponse`` occasionally miscalculates ``Content-Length`` when the file
    is generated just before returning. Reading the file into memory ensures the
    length header matches the actual content sent.
    """
    data = path.read_bytes()
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
    }
    return Response(content=data, media_type=media_type, headers=headers)


from pathlib import Path
from fastapi import UploadFile
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


def sanitize_for_sql(df: pd.DataFrame) -> pd.DataFrame:
    """Convert dtypes like ``timedelta`` to strings so SQLite can store them."""
    for col in df.columns:
        if pd.api.types.is_timedelta64_dtype(df[col]):
            df[col] = df[col].astype(str)
        elif df[col].dtype == object and df[col].map(
            lambda x: isinstance(x, datetime.timedelta)
        ).any():
            df[col] = df[col].apply(
                lambda x: str(x) if isinstance(x, datetime.timedelta) else x
            )
    return df


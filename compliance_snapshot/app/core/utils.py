from pathlib import Path
from fastapi import UploadFile

async def save_uploads(folder: Path, files: list[UploadFile]):
    """Save uploaded files to disk without loading into memory."""
    for f in files:
        dest = folder / f.filename
        with dest.open("wb") as out:
            while True:
                chunk = await f.read(1024 * 1024)  # 1 MB
                if not chunk:
                    break
                out.write(chunk)


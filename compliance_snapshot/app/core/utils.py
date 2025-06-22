from pathlib import Path
from fastapi import UploadFile

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


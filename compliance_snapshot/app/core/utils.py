 codex/create-upload-form-and-routes
from pathlib import Path
from fastapi import UploadFile


async def save_uploads(folder: Path, files: list[UploadFile]):
    """Save uploaded files asynchronously to the given folder."""
    for uploaded in files:
        dest = folder / uploaded.filename
        with dest.open("wb") as out_file:
            while True:
                chunk = await uploaded.read(1024)
                if not chunk:
                    break
                out_file.write(chunk)
        await uploaded.close()
=======
# Utility functions
>>>>>> main

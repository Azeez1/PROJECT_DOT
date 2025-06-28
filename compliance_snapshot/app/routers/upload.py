from fastapi import APIRouter, UploadFile, File, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uuid
import json

from ..core.utils import save_uploads, sanitize_for_sql
from ..services.processors import file_detector
import sqlite3
import pandas as pd
import logging
import json

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", tags=["health"])
async def root():
    return {"status": "alive"}

@router.get("/upload", response_class=HTMLResponse, tags=["ui"])
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@router.post("/generate", tags=["generate"])
async def generate(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)):
    """Save uploaded files and create database tables for each."""

    logger = logging.getLogger("upload")
    ticket = uuid.uuid4().hex
    folder = Path(f"/tmp/{ticket}")
    folder.mkdir(parents=True, exist_ok=True)

    await save_uploads(folder, files)

    db = sqlite3.connect(folder / "snapshot.db")
    errors: list[str] = []

    saved_files = [f for f in files if f.filename]
    if not saved_files:
        db.close()
        raise HTTPException(status_code=400, detail="no files uploaded")

    successes: list[str] = []
    failures: dict[str, str] = {}

    def record_failure(fname: str, exc: Exception):
        msg = str(exc)
        failures[fname] = msg
        logger.error("%s failed: %s", fname, msg)

    for file in saved_files:
        file_path = folder / Path(file.filename).name
        if not file_path.is_file():
            failures[file.filename] = "file missing after upload"
            logger.warning("File %s was not found after upload", file.filename)
            continue

        try:
            report_type, df = file_detector.detect_report_type(file_path)
        except Exception as exc:
            logger.exception("Failed to read %s", file.filename)
            record_failure(file.filename, exc)
            errors.append(f"{file.filename}: {exc}")
            continue

        table_name = report_type or "hos"
        try:
            sanitize_for_sql(df)
            df.to_sql(table_name, db, if_exists="replace", index=False)
            logger.info("Saved %s as '%s' table", file.filename, table_name)
            successes.append(file.filename)
        except Exception as exc:
            logger.exception("Failed to write %s to table %s", file.filename, table_name)
            record_failure(file.filename, exc)
            errors.append(f"{file.filename}: {exc}")

    summary = {
        "uploaded": len(saved_files),
        "processed": len(successes),
        "failed": failures,
    }

    with (folder / "summary.json").open("w") as fh:
        json.dump(summary, fh)

    logger.info("Upload summary: %s", summary)

    db.close()

    # persist any errors so the wizard can display them
    if errors:
        (folder / "errors.json").write_text(json.dumps(errors))

    from fastapi.responses import RedirectResponse
    return RedirectResponse(f"/wizard/{ticket}", status_code=303)

@router.get("/download/{ticket}", tags=["generate"])
async def download(ticket: str):
    """Return the generated PDF as a downloadable file."""
    pdf_path = Path(f"/tmp/{ticket}/ComplianceSnapshot.pdf")
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="snapshot not found")

    # FastAPI adds 'attachment' disposition when filename is provided
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"DOT_Compliance_{ticket[:8]}.pdf",
    )




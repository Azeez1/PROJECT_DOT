from fastapi import APIRouter, UploadFile, File, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uuid

from ..core.utils import save_uploads
from ..services.processors import file_detector
import sqlite3
import pandas as pd
import logging

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

    saved_files = [f for f in files if f.filename]
    if not saved_files:
        db.close()
        raise HTTPException(status_code=400, detail="no files uploaded")

    if len(saved_files) == 1:
        file = saved_files[0]
        file_path = folder / Path(file.filename).name
        try:
            if file_path.suffix.lower() == ".csv":
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, engine="openpyxl")
            df.to_sql("hos", db, if_exists="replace", index=False)
            logger.info("Single file mode: Saved %s as 'hos' table", file.filename)
        except Exception as exc:
            logger.exception("Failed to process %s", file.filename)
    else:
        for file in saved_files:
            file_path = folder / Path(file.filename).name
            if not file_path.is_file():
                logger.warning("File %s was not found after upload", file.filename)
                continue
            try:
                report_type, df = file_detector.detect_report_type(file_path)
            except Exception as exc:
                logger.exception("Type detection failed for %s", file.filename)
                continue

            table_name = report_type or "hos"
            try:
                df.to_sql(table_name, db, if_exists="replace", index=False)
                logger.info("Saved %s as '%s' table", file.filename, table_name)
            except Exception:
                logger.exception("Failed to write %s to table %s", file.filename, table_name)

    db.close()

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




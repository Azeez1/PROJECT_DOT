from fastapi import APIRouter, UploadFile, File, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uuid

from ..core.utils import save_uploads
from ..services.processors import file_detector
import sqlite3, pandas as pd

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
    ticket = uuid.uuid4().hex
    folder = Path(f"/tmp/{ticket}")
    folder.mkdir(parents=True, exist_ok=True)

    await save_uploads(folder, files)

    db = sqlite3.connect(folder / "snapshot.db")

    saved_files = [f for f in files if f.filename]

    if len(saved_files) == 1:
        file = saved_files[0]
        file_path = folder / Path(file.filename).name
        if file_path.is_file():
            try:
                if file_path.suffix.lower() == ".csv":
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path, engine="openpyxl")
                df.to_sql("hos", db, if_exists="replace", index=False)
                print(f"Single file mode: Saved {file.filename} as 'hos' table")
            except Exception as e:
                print("SQLite write error:", e)
    else:
        for file in saved_files:
            file_path = folder / Path(file.filename).name
            if not file_path.is_file():
                continue
            try:
                report_type, df = file_detector.detect_report_type(file_path)
                if report_type:
                    df.to_sql(report_type, db, if_exists="replace", index=False)
                    print(f"Multi-file mode: Saved {file.filename} as '{report_type}' table")
            except Exception as e:
                print(f"Error processing {file.filename}: {e}")
                try:
                    if file_path.suffix.lower() == ".csv":
                        df = pd.read_csv(file_path)
                    else:
                        df = pd.read_excel(file_path, engine="openpyxl")
                    df.to_sql("hos", db, if_exists="replace", index=False)
                    print(f"Fallback: Saved {file.filename} as 'hos' table")
                except Exception:
                    print(f"Failed to process {file.filename}")

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




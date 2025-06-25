from fastapi import APIRouter, UploadFile, File, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uuid

from ..core.utils import save_uploads
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

    sample_path = next((folder / Path(f.filename).name for f in files if f.filename), None)
    if sample_path and sample_path.is_file():
        try:
            if sample_path.suffix.lower() == ".csv":
                df = pd.read_csv(sample_path)
            else:
                df = pd.read_excel(sample_path, engine="openpyxl")
            db = sqlite3.connect(folder / "snapshot.db")
            df.to_sql("hos", db, if_exists="replace", index=False)
            db.close()
        except Exception as e:
            print("SQLite write error:", e)

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




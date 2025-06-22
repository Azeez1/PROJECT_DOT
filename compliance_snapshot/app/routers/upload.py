from fastapi import APIRouter, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uuid

from ..core.utils import save_uploads
from ..services.pdf_maker import build_placeholder_pdf  # stub for now

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

    output_pdf = folder / "snapshot.pdf"
    background_tasks.add_task(build_placeholder_pdf, output_pdf)

    return JSONResponse({"ticket": ticket, "download_url": f"/download/{ticket}"})

@router.get("/download/{ticket}", tags=["generate"])
async def download(ticket: str):
    pdf_path = Path(f"/tmp/{ticket}/snapshot.pdf")
    if not pdf_path.exists():
        return JSONResponse({"status": "processing"})
    return FileResponse(pdf_path, filename="ComplianceSnapshot.pdf")


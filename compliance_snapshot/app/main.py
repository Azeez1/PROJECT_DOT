from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .routers import upload
from .routers import wizard

app = FastAPI(
    title="Compliance Snapshot",
    description="One\u2011click DOT compliance PDF generator",
    version="0.1.0",
)

# Allow cross-origin requests during upload processing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(wizard.router)
app.mount("/static", StaticFiles(directory="static"), name="static")

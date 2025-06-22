from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routers import upload

app = FastAPI(
    title="Compliance Snapshot",
    description="One\u2011click DOT compliance PDF generator",
    version="0.1.0",
)

app.include_router(upload.router)
app.mount("/static", StaticFiles(directory="static"), name="static")

from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from . import __version__
from .config import load_settings
from .ocr import OcrError, OcrService

app = FastAPI(title="RapidOCR Offline API", version=__version__)
service = OcrService()


@app.get("/health")
def health() -> dict[str, Any]:
    """Return process health without forcing OCR model initialization."""

    settings = load_settings()
    return {
        "status": "ok",
        "version": __version__,
        "host": settings.host,
        "port": settings.port,
        "engine_initialized": service.engine_initialized,
    }


@app.post("/ocr")
async def recognize(
    file: UploadFile = File(...),
    render_dpi: int = Form(200),
    return_word_box: bool = Form(False),
) -> dict[str, Any]:
    """Run OCR for one uploaded image or PDF file."""

    data = await file.read()
    return service.recognize_upload(
        filename=file.filename or "upload",
        data=data,
        render_dpi=render_dpi,
        return_word_box=return_word_box,
    )


@app.exception_handler(OcrError)
async def handle_ocr_error(_, exc: OcrError) -> JSONResponse:
    """Return application errors in a stable JSON shape."""

    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

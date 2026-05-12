from typing import Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from . import __version__
from .config import load_settings
from .ocr import OcrError, OcrService

# Hard cap on uploads to keep memory bounded; 50 MB covers typical OCR jobs.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

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

    # Reject oversized uploads early; Starlette exposes the parsed multipart size.
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        raise OcrError(
            "file_too_large",
            f"Upload exceeds the {MAX_UPLOAD_BYTES} byte limit.",
            status_code=413,
        )

    data = await file.read()

    # Offload synchronous RapidOCR/PyMuPDF work so the event loop stays responsive
    # for concurrent requests and the /health endpoint. Pass the byte cap again
    # because file.size is not guaranteed for every UploadFile implementation.
    return await run_in_threadpool(
        service.recognize_upload,
        filename=file.filename or "upload",
        data=data,
        render_dpi=render_dpi,
        return_word_box=return_word_box,
        max_bytes=MAX_UPLOAD_BYTES,
    )


@app.exception_handler(OcrError)
async def handle_ocr_error(_: Request, exc: OcrError) -> JSONResponse:
    """Return application errors in a stable JSON shape."""

    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    """Wrap any unhandled exception so the contract stays JSON, not HTML."""

    payload = {"error": {"code": "internal_error", "message": str(exc)}}
    return JSONResponse(status_code=500, content=payload)

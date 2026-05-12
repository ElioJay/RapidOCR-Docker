from __future__ import annotations

import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterable

from .pdf import render_pdf_to_png_files

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
PDF_EXTENSION = ".pdf"


class OcrError(Exception):
    """Structured application error that can be returned by HTTP and CLI layers."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}


class OcrService:
    """Shared OCR service used by both the API and CLI entry points."""

    def __init__(
        self,
        engine_factory: Callable[[], Any] | None = None,
        pdf_renderer: Callable[[str | Path, str | Path, int], list[Path]] = render_pdf_to_png_files,
    ):
        self._engine_factory = engine_factory or self._create_default_engine
        self._pdf_renderer = pdf_renderer
        self._engine: Any | None = None

    @property
    def engine_initialized(self) -> bool:
        """Expose lazy engine state for health checks."""

        return self._engine is not None

    def recognize_upload(
        self,
        filename: str,
        data: bytes,
        render_dpi: int = 200,
        return_word_box: bool = False,
        max_bytes: int | None = None,
    ) -> dict[str, Any]:
        """Recognize an uploaded file by writing it to a temporary path first."""

        suffix = Path(filename).suffix.lower()
        self._validate_file_suffix(suffix)
        # Validate the actual bytes too; some upload adapters do not expose
        # a reliable size before the body is read.
        if max_bytes is not None and len(data) > max_bytes:
            raise OcrError(
                "file_too_large",
                f"Upload exceeds the {max_bytes} byte limit.",
                status_code=413,
            )

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(data)
                temp_path = Path(temp_file.name)

            result = self.recognize_path(
                temp_path,
                render_dpi=render_dpi,
                return_word_box=return_word_box,
                display_name=filename,
            )
            return result
        finally:
            # The upload copy is a single temporary file owned by this request.
            if temp_path and temp_path.exists():
                temp_path.unlink()

    def recognize_path(
        self,
        input_path: str | Path,
        render_dpi: int = 200,
        return_word_box: bool = False,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """Recognize one image or PDF file and return normalized JSON data."""

        source = Path(input_path)
        if not source.exists():
            raise OcrError("file_not_found", f"Input file does not exist: {source}", status_code=404)

        suffix = source.suffix.lower()
        self._validate_file_suffix(suffix)
        self._validate_render_dpi(render_dpi)

        start_time = perf_counter()
        if suffix == PDF_EXTENSION:
            result = self._recognize_pdf(source, render_dpi, return_word_box)
        else:
            page = self._recognize_image(source, page_number=1, return_word_box=return_word_box)
            result = {"file_type": "image", "pages": [page]}

        pages = result["pages"]
        text = "\n\n".join(page["text"] for page in pages if page["text"])

        return {
            "filename": display_name or source.name,
            "file_type": result["file_type"],
            "page_count": len(pages),
            "text": text,
            "pages": pages,
            "elapsed": round(perf_counter() - start_time, 6),
        }

    def _recognize_pdf(self, source: Path, render_dpi: int, return_word_box: bool) -> dict[str, Any]:
        """Render a PDF into pages and OCR each rendered image."""

        with tempfile.TemporaryDirectory(prefix="rapidocr-pdf-") as temp_dir:
            try:
                page_images = self._pdf_renderer(source, temp_dir, render_dpi)
            except Exception as exc:
                # Renderer failures usually mean the user supplied a corrupt
                # or unsupported PDF payload, so surface a 400-level error.
                raise OcrError("invalid_file", "PDF could not be opened or rendered.") from exc

            if not page_images:
                raise OcrError("empty_pdf", "PDF did not render any pages.")

            pages = [
                self._recognize_image(page_image, page_number=index, return_word_box=return_word_box)
                for index, page_image in enumerate(page_images, start=1)
            ]

        return {"file_type": "pdf", "pages": pages}

    def _recognize_image(self, image_path: str | Path, page_number: int, return_word_box: bool) -> dict[str, Any]:
        """Run RapidOCR on one image path and normalize one page result."""

        raw_result = self._get_engine()(str(image_path), return_word_box=return_word_box)
        return self._normalize_page(raw_result, page_number)

    def _get_engine(self) -> Any:
        """Create RapidOCR only when the first OCR request arrives."""

        if self._engine is None:
            self._engine = self._engine_factory()
        return self._engine

    @staticmethod
    def _create_default_engine() -> Any:
        """Create the default RapidOCR engine with ONNX Runtime CPU dependencies."""

        from rapidocr import RapidOCR

        return RapidOCR()

    @staticmethod
    def _normalize_page(raw_result: Any, page_number: int) -> dict[str, Any]:
        """Convert RapidOCR dataclass-like output into plain JSON-compatible data."""

        texts = list(getattr(raw_result, "txts", ()) or ())
        scores = list(getattr(raw_result, "scores", ()) or ())
        boxes = _to_json_value(getattr(raw_result, "boxes", None))
        word_results = _to_json_value(getattr(raw_result, "word_results", None))

        lines: list[dict[str, Any]] = []
        for index, text in enumerate(texts):
            line: dict[str, Any] = {
                "text": str(text),
                "score": _safe_float(scores[index]) if index < len(scores) else None,
                "box": boxes[index] if isinstance(boxes, list) and index < len(boxes) else None,
            }

            # Word-level boxes are optional and only emitted when RapidOCR returns them.
            if isinstance(word_results, list) and index < len(word_results) and word_results[index]:
                line["words"] = word_results[index]

            lines.append(line)

        page_text = "\n".join(line["text"] for line in lines if line["text"])
        elapsed = _safe_float(getattr(raw_result, "elapse", None))
        if elapsed is None:
            elapsed_list = getattr(raw_result, "elapse_list", None)
            elapsed = sum(_safe_float(value) or 0.0 for value in elapsed_list) if elapsed_list else None

        return {"page": page_number, "text": page_text, "lines": lines, "elapsed": elapsed}

    @staticmethod
    def _validate_file_suffix(suffix: str) -> None:
        if suffix == PDF_EXTENSION or suffix in IMAGE_EXTENSIONS:
            return
        raise OcrError("unsupported_file_type", "Only image and PDF files are supported.")

    @staticmethod
    def _validate_render_dpi(render_dpi: int) -> None:
        # Keep PDF rendering bounded so accidental huge DPI values do not exhaust memory.
        if render_dpi < 72 or render_dpi > 400:
            raise OcrError("invalid_render_dpi", "render_dpi must be between 72 and 400.")


def _to_json_value(value: Any) -> Any:
    """Convert numpy-like values and tuples into JSON-compatible values."""

    if value is None:
        return None
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, tuple):
        return [_to_json_value(item) for item in value]
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    # Recurse into dict values so nested numpy scalars in word-level results
    # (e.g. {"score": np.float32(...)}) become JSON-serializable.
    if isinstance(value, dict):
        return {key: _to_json_value(item) for key, item in value.items()}
    return value


def _safe_float(value: Any) -> float | None:
    """Convert numeric values to float while preserving missing values."""

    if value is None:
        return None
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None

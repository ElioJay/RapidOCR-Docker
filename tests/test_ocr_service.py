from pathlib import Path
from types import SimpleNamespace

import pytest

from rapidocr_offline.ocr import OcrError, OcrService


class FakeArray:
    def __init__(self, value):
        self.value = value

    def tolist(self):
        # Tests mimic numpy arrays without importing numpy.
        return self.value


class FakeEngine:
    def __init__(self):
        self.calls = []

    def __call__(self, image_path, return_word_box=False):
        # Record inputs so tests verify image and PDF paths share the same OCR path.
        self.calls.append((Path(image_path).suffix.lower(), return_word_box))
        return SimpleNamespace(
            txts=("第一行", "第二行"),
            scores=(0.99, 0.88),
            boxes=FakeArray(
                [
                    [[1, 2], [11, 2], [11, 8], [1, 8]],
                    [[2, 12], [20, 12], [20, 18], [2, 18]],
                ]
            ),
            elapse=0.12,
        )


def render_two_fake_pdf_pages(pdf_path, output_dir, dpi):
    # The renderer writes page files because the OCR service should pass paths to RapidOCR.
    first = Path(output_dir) / "page-1.png"
    second = Path(output_dir) / "page-2.png"
    first.write_bytes(b"fake-page-1")
    second.write_bytes(b"fake-page-2")
    return [first, second]


def render_broken_pdf(pdf_path, output_dir, dpi):
    # Simulate PyMuPDF rejecting a corrupt or non-PDF payload.
    raise RuntimeError("cannot render pdf")


def test_recognize_image_returns_merged_text_and_structured_lines(tmp_path):
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"fake-image")
    engine = FakeEngine()
    service = OcrService(engine_factory=lambda: engine, pdf_renderer=render_two_fake_pdf_pages)

    result = service.recognize_path(image_path, render_dpi=200, return_word_box=True)

    assert result["filename"] == "input.png"
    assert result["file_type"] == "image"
    assert result["page_count"] == 1
    assert result["text"] == "第一行\n第二行"
    assert result["pages"][0]["page"] == 1
    assert result["pages"][0]["lines"][0] == {
        "text": "第一行",
        "score": 0.99,
        "box": [[1, 2], [11, 2], [11, 8], [1, 8]],
    }
    assert engine.calls == [(".png", True)]


def test_recognize_pdf_renders_each_page_and_merges_page_text(tmp_path):
    pdf_path = tmp_path / "input.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    engine = FakeEngine()
    service = OcrService(engine_factory=lambda: engine, pdf_renderer=render_two_fake_pdf_pages)

    result = service.recognize_path(pdf_path, render_dpi=180, return_word_box=False)

    assert result["filename"] == "input.pdf"
    assert result["file_type"] == "pdf"
    assert result["page_count"] == 2
    assert result["text"] == "第一行\n第二行\n\n第一行\n第二行"
    assert [page["page"] for page in result["pages"]] == [1, 2]
    assert engine.calls == [(".png", False), (".png", False)]


def test_recognize_rejects_unsupported_file_type(tmp_path):
    input_path = tmp_path / "notes.txt"
    input_path.write_text("not an image", encoding="utf-8")
    service = OcrService(engine_factory=FakeEngine, pdf_renderer=render_two_fake_pdf_pages)

    with pytest.raises(OcrError) as exc_info:
        service.recognize_path(input_path)

    assert exc_info.value.code == "unsupported_file_type"
    assert "image and PDF" in exc_info.value.message


def test_recognize_pdf_wraps_renderer_errors_as_input_errors(tmp_path):
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_bytes(b"not a pdf")
    service = OcrService(engine_factory=FakeEngine, pdf_renderer=render_broken_pdf)

    with pytest.raises(OcrError) as exc_info:
        service.recognize_path(pdf_path)

    assert exc_info.value.code == "invalid_file"
    assert exc_info.value.status_code == 400


def test_recognize_upload_rejects_data_over_explicit_size_limit():
    service = OcrService(engine_factory=FakeEngine, pdf_renderer=render_two_fake_pdf_pages)

    with pytest.raises(OcrError) as exc_info:
        service.recognize_upload("input.png", b"too-large", max_bytes=4)

    assert exc_info.value.code == "file_too_large"
    assert exc_info.value.status_code == 413

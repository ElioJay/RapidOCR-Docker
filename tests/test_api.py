import asyncio
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from rapidocr_offline import api
from rapidocr_offline.api import _read_upload_with_cap
from rapidocr_offline.ocr import OcrError


@pytest.fixture
def client():
    # The default OcrService never initializes RapidOCR until the first OCR
    # call, so it is safe to use the real app for tests that short-circuit
    # before reaching the engine (size-cap rejections).
    return TestClient(api.app)


def test_health_endpoint_returns_ok(client):
    # Sanity check that the test harness wires up without touching RapidOCR.
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["engine_initialized"] is False


def test_ocr_endpoint_returns_413_when_upload_exceeds_cap(monkeypatch, client):
    # Shrink the cap so the test does not have to ship 50 MB of payload.
    monkeypatch.setattr(api, "MAX_UPLOAD_BYTES", 16)

    response = client.post(
        "/ocr",
        files={"file": ("upload.png", BytesIO(b"x" * 64), "image/png")},
    )

    # Asserts the regression-critical contract: forgetting MAX_UPLOAD_BYTES,
    # the streaming guard, or the OcrError exception handler would all break
    # this assertion.
    assert response.status_code == 413
    assert response.json() == {
        "error": {"code": "file_too_large", "message": "Upload exceeds the 16 byte limit."}
    }


class _FakeStreamingUpload:
    """Minimal ``UploadFile`` stand-in whose size attribute is ``None``.

    Mirrors the scenario the streaming guard is meant to defend against:
    the upload adapter does not expose a length up front.
    """

    def __init__(self, chunks: list[bytes]):
        # Copy so iterating the test fixture does not mutate the source list.
        self._chunks = list(chunks)
        self.size = None  # Force the slow-path branch in api.recognize.

    async def read(self, size: int = -1) -> bytes:
        # Yield one queued chunk per call; an empty bytes value marks EOF.
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


def test_read_upload_with_cap_rejects_streamed_overflow():
    # Two 8-byte chunks total 16 bytes — pushed across a 10-byte cap.
    upload = _FakeStreamingUpload([b"a" * 8, b"b" * 8])

    with pytest.raises(OcrError) as exc_info:
        # Drive the coroutine with asyncio.run so we do not depend on
        # pytest-asyncio (kept out of requirements-dev.txt intentionally).
        asyncio.run(_read_upload_with_cap(upload, max_bytes=10))

    assert exc_info.value.code == "file_too_large"
    assert exc_info.value.status_code == 413


def test_read_upload_with_cap_returns_body_when_under_cap():
    # Exactly equal to the cap must be accepted; the guard uses strict ``>``.
    upload = _FakeStreamingUpload([b"abcd", b"efgh"])

    data = asyncio.run(_read_upload_with_cap(upload, max_bytes=8))

    assert data == b"abcdefgh"

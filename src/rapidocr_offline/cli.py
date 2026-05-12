from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .ocr import OcrError, OcrService


def build_parser() -> argparse.ArgumentParser:
    """Create the OCR command parser."""

    parser = argparse.ArgumentParser(prog="ocr", description="Run RapidOCR on an image or PDF.")
    parser.add_argument("input", help="Input image or PDF path inside the container.")
    parser.add_argument("--output", "-o", help="Write JSON result to this file instead of stdout.")
    parser.add_argument("--render-dpi", type=int, default=200, help="PDF render DPI, from 72 to 400.")
    parser.add_argument("--return-word-box", action="store_true", help="Return word-level boxes when supported.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def run_ocr(args: argparse.Namespace, service: OcrService | None = None) -> dict:
    """Run OCR from parsed CLI arguments."""

    ocr_service = service or OcrService()
    result = ocr_service.recognize_path(
        args.input,
        render_dpi=args.render_dpi,
        return_word_box=args.return_word_box,
    )
    json_text = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_text + "\n", encoding="utf-8")
    else:
        print(json_text)

    return result


def main(argv: Sequence[str] | None = None) -> int:
    """CLI process entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        run_ocr(args)
        return 0
    except OcrError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False), file=sys.stderr)
        return exc.status_code
    except Exception as exc:  # pragma: no cover - last-resort process boundary.
        payload = {"error": {"code": "internal_error", "message": str(exc)}}
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - module execution boundary.
    raise SystemExit(main())

from pathlib import Path


def render_pdf_to_png_files(pdf_path: str | Path, output_dir: str | Path, dpi: int) -> list[Path]:
    """Render every PDF page to a PNG file and return the generated paths."""

    # PyMuPDF is imported lazily so unit tests can run without the runtime dependency.
    try:
        import pymupdf as fitz
    except ImportError:  # pragma: no cover - compatibility for older PyMuPDF releases.
        import fitz  # type: ignore[no-redef]

    source = Path(pdf_path)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    rendered_pages: list[Path] = []
    with fitz.open(source) as document:
        for index, page in enumerate(document, start=1):
            # alpha=False keeps empty PDF background white and reduces memory use.
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)
            output_path = target_dir / f"page-{index}.png"
            pixmap.save(output_path)
            rendered_pages.append(output_path)

    return rendered_pages

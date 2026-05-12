import os

import uvicorn

from .config import load_settings


def main() -> None:
    """Start the HTTP server using environment-based host and port settings."""

    settings = load_settings()
    uvicorn.run(
        "rapidocr_offline.api:app",
        host=settings.host,
        port=settings.port,
        log_level=os.environ.get("LOG_LEVEL", "info"),
    )


if __name__ == "__main__":  # pragma: no cover - module execution boundary.
    main()

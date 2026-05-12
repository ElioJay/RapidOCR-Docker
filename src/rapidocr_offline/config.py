import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AppSettings:
    """Runtime settings loaded from environment variables."""

    host: str = "0.0.0.0"
    port: int = 8000


def load_settings(environ: Mapping[str, str] | None = None) -> AppSettings:
    """Load HTTP server settings from the environment."""

    source = os.environ if environ is None else environ
    host = source.get("APP_HOST", "0.0.0.0")
    raw_port = source.get("APP_PORT", "8000")

    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("APP_PORT must be an integer between 1 and 65535.") from exc

    if port < 1 or port > 65535:
        raise ValueError("APP_PORT must be an integer between 1 and 65535.")

    return AppSettings(host=host, port=port)

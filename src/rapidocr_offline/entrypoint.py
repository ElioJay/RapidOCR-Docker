from __future__ import annotations

import sys
from typing import Sequence

from . import cli, server


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch Docker commands to either server or CLI mode."""

    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] == "server":
        server.main()
        return 0

    if args[0] == "ocr":
        return cli.main(args[1:])

    # Treat unknown first arguments as direct CLI input for convenience.
    return cli.main(args)


if __name__ == "__main__":  # pragma: no cover - module execution boundary.
    raise SystemExit(main())

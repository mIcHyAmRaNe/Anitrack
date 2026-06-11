"""anitrack root entry point — delegates to app.main."""

from __future__ import annotations

from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())

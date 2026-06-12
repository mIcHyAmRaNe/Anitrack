# AGENTS.md
Drop-in operating instructions for coding agents. Read this file before every task.

**Working code only. Finish the job. Plausibility is not correctness.**

---

## Docs management

- When you need to search docs, use Context7.

---

## Package management

- This project uses uv for all package management
- Never run commands directly (python, pytest, etc.)
- Always prefix commands with `uv run <command>`
- Example: `uv run python script.py` not `python script.py`
- Example: `uv run pytest` not `pytest`

---

## Build, lint, test

```bash
uv run ruff check          # lint
uv run python smoke_test.py       # headless import + window build test
uv run python behavior_test.py    # end-to-end behavior test (no network)
uv run python build.py            # builds dist/Anitrack.exe via PyInstaller
```

- No formal test framework. The two `*_test.py` files are standalone scripts.
- Both tests run headless (`QT_QPA_PLATFORM=offscreen`) and never hit the network.
- CI runs on Windows only (see `.github/workflows/ci.yml`).

---

## Two config systems (don't mix them up)

1. **`config/config.json` → `AppConfig`** — holds all UI constants (colors, sizes, spacing, API settings). Loaded once at startup. This is the single source of truth for user-facing values.
2. **`app/config/settings.py` → `cfg` (QConfig)** — holds runtime user preferences (theme mode, download cover toggle, local anime folders). Managed by `qfluentwidgets`.

When adding a UI constant, add it to `config/config.json` + an `AppConfig` classmethod. Never hardcode in widget code.

---

## Architecture

```
main.py → app/main.py (entry point)
app/
  config/     AppConfig (UI constants) + cfg (user prefs)
  models/     Anime dataclass, Library singleton
  services/   Jikan API client, image cache (QNetworkAccessManager)
  theme/      Flavor enum (mocha/latte), theme helpers
  ui/
    main_window.py    Top-level FluentWindow
    signal_bus.py     signalBus singleton for cross-component signals
    pages/            home, list, detail, settings, about
    widgets/          anime_card, character_card, etc.
```

- **Theme**: Mocha = dark, Latte = light. Stored in QConfig (`cfg.themeMode`).
- **Signal bus**: `app/ui/signal_bus.py` — `signalBus` is the global singleton. Components communicate via its signals (libraryChanged, openAnimeDetail, themeChanged, etc.).
- **Library**: Singleton via `get_library()`. Stored at `%LOCALAPPDATA%/anitrack/library.json` (Windows).
- **API**: Jikan v4 (unofficial MyAnimeList API). Disk-cached responses in platform cache dir. Rate-limited with exponential backoff.
- **Entry point**: `pyproject.toml` defines `anitrack = "app.main:main"`.

---

## Configuration: no hardcoded UI values

**`config/config.json` is the single source of truth for all user-facing values. `AppConfig` is the only way to read them. Never hardcode.**

Rules:
- **Never** write a raw number or color string directly in a widget file. If `config.json` does not have a key for it, add one there (and optionally a fallback in `_DEFAULTS`).
- CSS strings in `setStyleSheet(...)` must use `AppConfig.get(...)` for every numeric or color value. No inline literals.
- **Exception**: Pure layout-only values inherent to widget structure (e.g., `QVBoxLayout` default spacing of 0) are acceptable.

When modifying a configuration file:
1. Read the existing file.
2. Identify the minimal set of keys that must change.
3. Change only those keys.
4. Verify that no unrelated key was added, removed, renamed, or reordered.

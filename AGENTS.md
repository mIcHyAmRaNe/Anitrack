# AGENTS.md
Drop-in operating instructions for coding agents. Read this file before every task.

**Working code only. Finish the job. Plausibility is not correctness.**

---

## Package management

- This project uses **uv** for all package management.
- Never run commands directly (`python`, `pytest`, etc.).
- Always prefix commands with `uv run <command>`.
- Example: `uv run python script.py` not `python script.py`.

---

## Build, lint, test

```bash
uv sync                          # install deps (required first time)
uv run ruff check                # lint
uv run python smoke_test.py      # headless import + window build test
uv run python behavior_test.py   # end-to-end behavior test (no network)
uv run python build.py           # builds dist/Anitrack.exe via PyInstaller
```

- No formal test framework. The two `*_test.py` files are standalone scripts.
- Both tests run headless (`QT_QPA_PLATFORM=offscreen`) and never hit the network.
- CI runs on **Windows only** (`.github/workflows/ci.yml`): `lint` job → `build` job.
- `Anitrack.spec` exists alongside `build.py` — `build.py` regenerates it each run.

---

## Architecture

```
main.py → app/main.py (entry point)
app/
  config/     AppConfig (hardcoded defaults) + cfg (QConfig user prefs)
  models/     Anime dataclass, Library singleton, AnimeStatus, STATUS_FLUENT_ICONS
  services/   Jikan API client (httpx + diskcache), image cache (QNetworkAccessManager)
  ui/
    main_window.py    Top-level FluentWindow
    signal_bus.py     signalBus singleton for cross-component signals
    workers.py        QThread workers for search, suggestions, detail fetch
    pages/            home, list, detail, settings, about
    widgets/          base_card, anime_card, character_card, etc.
```

- **No custom theming**: The app uses default qfluentwidgets styling. All `setStyleSheet` calls and theme helpers have been removed. Do not add custom styling.
- **Signal bus**: `app/ui/signal_bus.py` — `signalBus` is the global singleton. Components communicate via its signals (libraryChanged, openAnimeDetail, goBack, etc.).
- **Library**: Singleton via `get_library()`. Stored at platform-specific path: `%LOCALAPPDATA%/anitrack/library.json` (Windows) or `~/.local/share/anitrack/library.json` (Linux). Atomic writes via tempfile + `os.replace`.
- **API**: Jikan v4 (unofficial MyAnimeList API). `JikanClient` is a singleton via `client()`. Disk-cached responses via `diskcache` in platform cache dir. Rate-limited with exponential backoff. Uses `httpx` (sync client).
- **Image cache**: `ImageLoader` singleton via `image_loader()`. Uses `QNetworkAccessManager` for async fetches. File-based disk cache with 30-day eviction.
- **Workers**: `SearchWorker`, `SuggestionsWorker`, `FetchDetailWorker` in `app/ui/workers.py` — all QThread subclasses. API calls run off the main thread.
- **Entry point**: `pyproject.toml` defines `anitrack = "app.main:main"`.

---

## Configuration

- `AppConfig` (`app/config/app_config.py`) holds hardcoded defaults for app metadata, API settings, and path utilities. No file I/O — all values are constants.
- `cfg` (`app/config/settings.py`) holds runtime user preferences (download cover toggle, local anime folders). Managed by `qfluentwidgets`.
- There is no `config/config.json` and no custom theme system.

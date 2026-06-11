# Anitrack

A desktop application to track the anime you watch, have watched, and plan to watch. Built with PyQt6 and backed by the MyAnimeList database via the Jikan API.

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white&style=for-the-badge)
![PyQt6](https://img.shields.io/badge/PyQt6-Green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

## Features

- **Search** the MyAnimeList database by title
- **View detailed info**: synopsis, score, rank, genres, characters, relations, recommendations, and trailers
- **Track your library** with statuses: Watching, Completed, On Hold, Dropped, Plan to Watch
- **Favorite** anime to pin them at the top of your library
- **Filter and sort** your library by type, genre, status, and score
- **Bulk operations**: select and delete multiple entries at once
- **Import/restore** your library from backup JSON files
- **Dark and light themes** (Mocha / Latte with a Catppuccin-inspired palette)
- **Keyboard shortcuts** (configurable in Settings)

## Screenshots

> Add screenshots here to showcase the application.

## Prerequisites

- Python 3.12 or later (developed on 3.14)
- [uv](https://docs.astral.sh/uv/) package manager

## Building

```bash
# Clone the repository
git clone https://github.com/your-username/anitrack.git
cd anitrack

# Install dependencies
uv sync

uv run python build.py
```

This produces a single-file executable at `dist/Anitrack.exe` (Windows) via PyInstaller.


## Testing

There is no formal test framework. Run the standalone smoke tests to verify the app builds correctly:

```bash
uv run python smoke_test.py
uv run python behavior_test.py
```

Both tests run headless (no display required) and do not make network requests.

## Linting

```bash
uv run ruff check
```

## How It Works

- **API**: Uses [Jikan API v4](https://docs.api.jikan.moe/) (unofficial MyAnimeList REST API) with rate limiting, exponential backoff retry, and disk-based response caching.
- **Library storage**: Saved as a JSON file in your platform's data directory (`%LOCALAPPDATA%/anitrack/library.json` on Windows).
- **Image loading**: Asynchronous via `QNetworkAccessManager` with a file-based disk cache (30-day eviction).

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push to the branch and open a Pull Request

## License

MIT

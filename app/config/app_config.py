from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from loguru import logger


def _default_config_path() -> Path:
    return Path(__file__).parent.parent.parent / "config" / "config.json"


_DEFAULTS: dict[str, Any] = {
    "app": {"name": "Anitrack", "version": "0.1.0"},
    "theme": {
        "mode": "Dark",
        "dark": {"text": "#cdd6f4", "background": "#272727"},
        "light": {"text": "#4c4f69", "background": "#f9f9f9"},
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class AppConfig:
    _data: dict[str, Any] = {}

    @classmethod
    def load(cls, path: str | Path | None = None) -> None:
        cls._data = _deep_merge(_DEFAULTS, {})
        if path is None:
            path = _default_config_path()
        else:
            path = Path(path)
        try:
            overrides = json.loads(path.read_text(encoding="utf-8"))
            cls._data = _deep_merge(cls._data, overrides)
            logger.info("Config loaded from {}", path)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load config from {}: {}", path, e)

    @classmethod
    def _get(cls, *keys: str) -> Any:
        if not cls._data:
            cls.load()
        node = cls._data
        for key in keys:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
            if node is None:
                return None
        return node

    @classmethod
    def get(cls, *keys: str) -> Any:
        return cls._get(*keys)

    # -- app --
    @classmethod
    def app_name(cls) -> str:
        return cls._get("app", "name")

    @classmethod
    def app_version(cls) -> str:
        return cls._get("app", "version")

    @classmethod
    def font_family(cls) -> str:
        return cls._get("app", "font_family")

    @classmethod
    def font_size(cls) -> int:
        return cls._get("app", "font_size")

    @classmethod
    def subtitle_font_size(cls) -> int:
        return cls._get("app", "subtitle_font_size")

    # -- theme --
    @classmethod
    def theme_mode(cls) -> str:
        return cls._get("theme", "mode")

    @classmethod
    def _palette(cls, dark: bool) -> dict:
        key = "dark" if dark else "light"
        return cls._get("theme", key) or {}

    @classmethod
    def text_color(cls, dark: bool) -> str:
        return cls._palette(dark).get("text", "")

    @classmethod
    def muted_color(cls, dark: bool) -> str:
        return cls._palette(dark).get("muted", "")

    @classmethod
    def background_color(cls, dark: bool) -> str:
        return cls._palette(dark).get("background", "")

    @classmethod
    def surface_color(cls, dark: bool) -> str:
        return cls._palette(dark).get("surface", "")

    @classmethod
    def title_color(cls, dark: bool) -> str:
        return cls._palette(dark).get("title", "")

    @classmethod
    def pill_bg(cls, dark: bool) -> str:
        return cls._palette(dark).get("pill_bg", "")

    @classmethod
    def pill_text(cls, dark: bool) -> str:
        return cls._palette(dark).get("pill_text", "")

    # -- ui: card --
    @classmethod
    def card_cover_w(cls) -> int:
        return cls._get("ui", "card", "cover_w")

    @classmethod
    def card_cover_h(cls) -> int:
        return cls._get("ui", "card", "cover_h")

    @classmethod
    def detail_cover_w(cls) -> int:
        return cls._get("ui", "card", "detail_cover_w")

    @classmethod
    def detail_cover_h(cls) -> int:
        return cls._get("ui", "card", "detail_cover_h")

    @classmethod
    def card_radius(cls) -> int:
        return cls._get("ui", "card", "radius")

    @classmethod
    def badge_size(cls) -> int:
        return cls._get("ui", "card", "badge_size")

    @classmethod
    def dim_opacity(cls) -> float:
        return cls._get("ui", "card", "dim_opacity")

    @classmethod
    def hover_opacity(cls) -> float:
        return cls._get("ui", "card", "hover_opacity")

    @classmethod
    def anim_duration_ms(cls) -> int:
        return cls._get("ui", "card", "anim_duration_ms")

    @classmethod
    def hover_debounce_ms(cls) -> int:
        return cls._get("ui", "card", "hover_debounce_ms")

    @classmethod
    def small_card_w(cls) -> int:
        return cls._get("ui", "card", "small_w")

    @classmethod
    def small_card_h(cls) -> int:
        return cls._get("ui", "card", "small_h")

    @classmethod
    def badge_font_size(cls) -> int:
        return cls._get("ui", "card", "badge_font_size")

    @classmethod
    def badge_font_weight(cls) -> int:
        return cls._get("ui", "card", "badge_font_weight")

    @classmethod
    def badge_padding(cls) -> str:
        return cls._get("ui", "card", "badge_padding")

    @classmethod
    def heart_offset_x(cls) -> int:
        return cls._get("ui", "card", "heart_offset_x")

    @classmethod
    def heart_offset_y(cls) -> int:
        return cls._get("ui", "card", "heart_offset_y")

    @classmethod
    def select_offset_x(cls) -> int:
        return cls._get("ui", "card", "select_offset_x")

    @classmethod
    def select_offset_y(cls) -> int:
        return cls._get("ui", "card", "select_offset_y")

    @classmethod
    def status_badge_offset_x(cls) -> int:
        return cls._get("ui", "card", "status_badge_offset_x")

    @classmethod
    def status_badge_offset_y(cls) -> int:
        return cls._get("ui", "card", "status_badge_offset_y")

    # -- ui: character --
    @classmethod
    def char_img_size(cls) -> int:
        return cls._get("ui", "character", "img_size")

    @classmethod
    def char_card_w(cls) -> int:
        return cls._get("ui", "character", "card_w")

    @classmethod
    def char_card_h(cls) -> int:
        return cls._get("ui", "character", "card_h")

    @classmethod
    def char_radius(cls) -> int:
        return cls._get("ui", "character", "radius")

    @classmethod
    def char_avatar_radius(cls) -> int:
        return cls._get("ui", "character", "avatar_radius")

    # -- ui: table --
    @classmethod
    def thumb_w(cls) -> int:
        return cls._get("ui", "table", "thumb_w")

    @classmethod
    def thumb_h(cls) -> int:
        return cls._get("ui", "table", "thumb_h")

    @classmethod
    def table_row_height(cls) -> int:
        return cls._get("ui", "table", "row_height")

    @classmethod
    def table_column_widths(cls) -> list[int]:
        return cls._get("ui", "table", "column_widths")

    @classmethod
    def table_title_col_extra(cls) -> int:
        return cls._get("ui", "table", "title_col_extra")

    @classmethod
    def table_header_fallback_height(cls) -> int:
        return cls._get("ui", "table", "header_fallback_height")

    # -- ui: trailer --
    @classmethod
    def trailer_thumb_h(cls) -> int:
        return cls._get("ui", "trailer", "thumb_h")

    # -- ui: about --
    @classmethod
    def about_icon_size(cls) -> int:
        return cls._get("ui", "about", "icon_size")

    @classmethod
    def about_card_radius(cls) -> int:
        return cls._get("ui", "about", "card_radius")

    @classmethod
    def about_chip_icon_size(cls) -> int:
        return cls._get("ui", "about", "chip_icon_size")

    @classmethod
    def about_chip_radius(cls) -> int:
        return cls._get("ui", "about", "chip_radius")

    @classmethod
    def about_tagline_padding(cls) -> str:
        return cls._get("ui", "about", "tagline_padding")

    @classmethod
    def about_icon_spacing(cls) -> int:
        return cls._get("ui", "about", "icon_spacing")

    @classmethod
    def about_version_spacing(cls) -> int:
        return cls._get("ui", "about", "version_spacing")

    @classmethod
    def about_before_info_spacing(cls) -> int:
        return cls._get("ui", "about", "before_info_spacing")

    @classmethod
    def about_body_after_spacing(cls) -> int:
        return cls._get("ui", "about", "body_after_spacing")

    # -- ui: accent --
    @classmethod
    def selection_color(cls) -> str:
        return cls._get("ui", "accent", "selection")

    @classmethod
    def badge_bg_color(cls) -> str:
        return cls._get("ui", "accent", "badge_bg")

    @classmethod
    def danger_color(cls) -> str:
        return cls._get("ui", "accent", "danger")

    # -- ui: detail --
    @classmethod
    def detail_spinner_size(cls) -> int:
        return cls._get("ui", "detail", "spinner_size")

    @classmethod
    def detail_scroll_height_offset(cls) -> int:
        return cls._get("ui", "detail", "scroll_height_offset")

    @classmethod
    def detail_header_spacing(cls) -> int:
        return cls._get("ui", "detail", "header_spacing")

    @classmethod
    def detail_genres_spacing(cls) -> int:
        return cls._get("ui", "detail", "genres_spacing")

    @classmethod
    def detail_spinner_margin_top(cls) -> int:
        return cls._get("ui", "detail", "spinner_margin_top")

    @classmethod
    def detail_url_spacing(cls) -> int:
        return cls._get("ui", "detail", "url_spacing")

    # -- ui: home --
    @classmethod
    def home_subtitle_spacing(cls) -> int:
        return cls._get("ui", "home", "subtitle_spacing")

    @classmethod
    def home_search_spacing(cls) -> int:
        return cls._get("ui", "home", "search_spacing")

    # -- ui: list --
    @classmethod
    def list_filter_row_spacing(cls) -> int:
        return cls._get("ui", "list", "filter_row_spacing")

    @classmethod
    def list_selection_toolbar_spacing(cls) -> int:
        return cls._get("ui", "list", "selection_toolbar_spacing")

    @classmethod
    def list_title_spacing(cls) -> int:
        return cls._get("ui", "list", "title_spacing")

    # -- ui: settings --
    @classmethod
    def settings_title_spacing(cls) -> int:
        return cls._get("ui", "settings", "title_spacing")

    # -- ui: timing --
    @classmethod
    def search_debounce_ms(cls) -> int:
        return cls._get("ui", "timing", "search_debounce_ms")

    @classmethod
    def suggestions_delay_ms(cls) -> int:
        return cls._get("ui", "timing", "suggestions_delay_ms")

    @classmethod
    def long_press_ms(cls) -> int:
        return cls._get("ui", "timing", "long_press_ms")

    @classmethod
    def drag_threshold(cls) -> int:
        return cls._get("ui", "timing", "drag_threshold")

    @classmethod
    def toast_duration_ms(cls) -> int:
        return cls._get("ui", "timing", "toast_duration_ms")

    @classmethod
    def tooltip_filter_ms(cls) -> int:
        return cls._get("ui", "timing", "tooltip_filter_ms")

    # -- ui: limits --
    @classmethod
    def search_results_limit(cls) -> int:
        return cls._get("ui", "limits", "search_results")

    @classmethod
    def suggestions_limit(cls) -> int:
        return cls._get("ui", "limits", "suggestions")

    @classmethod
    def characters_limit(cls) -> int:
        return cls._get("ui", "limits", "characters")

    @classmethod
    def api_limit_max(cls) -> int:
        return cls._get("ui", "limits", "api_limit_max")

    # -- api --
    @classmethod
    def api_base_url(cls) -> str:
        return cls._get("api", "base_url")

    @classmethod
    def api_timeout(cls) -> float:
        return cls._get("api", "timeout_seconds")

    @classmethod
    def api_max_retries(cls) -> int:
        return cls._get("api", "max_retries")

    @classmethod
    def api_min_interval(cls) -> float:
        return cls._get("api", "min_interval_seconds")

    @classmethod
    def cache_dir(cls) -> Path:
        if os.name == "nt":
            base = Path(
                os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            )
        else:
            base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        path = base / "anitrack" / "cache"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def api_cache_dir(cls) -> Path:
        path = cls.cache_dir() / "api_responses"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def logs_dir(cls) -> Path:
        if os.name == "nt":
            base = Path(
                os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            )
        else:
            base = Path(
                os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
            )
        path = base / "anitrack" / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

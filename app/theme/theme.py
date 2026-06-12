from __future__ import annotations

from enum import Enum

from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import Theme, isDarkTheme, setTheme

from ..config.app_config import AppConfig


class Flavor(str, Enum):
    FRAPPE = "frappe"
    LATTE = "latte"


STATUS_FLUENT_ICONS = {
    "watching": FIF.VIEW,
    "completed": FIF.COMPLETED,
    "on_hold": FIF.PAUSE,
    "dropped": FIF.DELETE,
    "plan_to_watch": FIF.CALENDAR,
}


def init_theme(flavor: Flavor = Flavor.FRAPPE) -> None:
    setTheme(Theme.DARK if flavor is Flavor.FRAPPE else Theme.LIGHT)


def _dark() -> bool:
    return isDarkTheme()


def text_color() -> str:
    return AppConfig.text_color(_dark())


def muted_color() -> str:
    return AppConfig.muted_color(_dark())


def interface_background() -> str:
    return AppConfig.background_color(_dark())


def surface_color() -> str:
    return AppConfig.surface_color(_dark())


def title_color() -> str:
    return AppConfig.title_color(_dark())


def pill_bg() -> str:
    return AppConfig.pill_bg(_dark())


def pill_text() -> str:
    return AppConfig.pill_text(_dark())


def window_stylesheet() -> str:
    bg = interface_background()
    sc = surface_color()
    return (
        f"FluentWindow {{ background: {bg}; }}"
        f"QStackedWidget {{ background: {bg}; }}"
        f"NavigationInterface {{ background: {sc}; }}"
    )

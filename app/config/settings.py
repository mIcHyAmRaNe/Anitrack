from __future__ import annotations

from qfluentwidgets import (
    BoolValidator,
    ConfigItem,
    FolderListValidator,
    OptionsConfigItem,
    OptionsValidator,
    QConfig,
)

from ..theme.theme import Flavor


class Config(QConfig):
    themeMode = OptionsConfigItem(
        "MainWindow",
        "ThemeMode",
        Flavor.FRAPPE.value,
        OptionsValidator([f.value for f in Flavor]),
    )
    downloadCover = ConfigItem("MainWindow", "DownloadCover", True, BoolValidator())
    localAnimeFolders = ConfigItem(
        "Library", "LocalAnimeFolders", [], FolderListValidator()
    )


cfg = Config()


def current_flavor() -> Flavor:
    raw = cfg.get(cfg.themeMode)
    try:
        return Flavor(raw)
    except ValueError:
        return Flavor.FRAPPE

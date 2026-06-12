from __future__ import annotations

from qfluentwidgets import (
    ConfigItem,
    FolderListValidator,
    QConfig,
)


class Config(QConfig):
    localAnimeFolders = ConfigItem(
        "Library", "LocalAnimeFolders", [], FolderListValidator()
    )


cfg = Config()

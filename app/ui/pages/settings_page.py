from __future__ import annotations

from loguru import logger
from PyQt6.QtCore import QSettings, QStandardPaths, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QKeySequenceEdit,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    ExpandGroupSettingCard,
    FolderListSettingCard,
    MessageBox,
    PushSettingCard,
    ScrollArea,
    SettingCard,
    SettingCardGroup,
    TitleLabel,
)
from qfluentwidgets import FluentIcon as FIF

from ...config.settings import cfg
from ...models.library import get_library, library_path
from ..signal_bus import signalBus


class _ShortcutDialog(QDialog):
    def __init__(self, current: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set Shortcut")
        self._edit = QKeySequenceEdit(QKeySequence(current), self)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Press the new shortcut:"))
        layout.addWidget(self._edit)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def key_sequence(self) -> str:
        return self._edit.keySequence().toString()


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsInterface")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.scrollArea = ScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scrollArea.enableTransparentBackground()
        self.scrollArea.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
        )
        viewport = self.scrollArea.viewport()
        if viewport is not None:
            viewport.setStyleSheet("background:transparent;")

        self.scrollArea.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.host = QWidget(self.scrollArea)
        self.hostLayout = QVBoxLayout(self.host)
        self.hostLayout.setContentsMargins(36, 28, 36, 28)
        self.hostLayout.setSpacing(12)
        self.host.setLayout(self.hostLayout)
        self.scrollArea.setWidget(self.host)

        self.titleLabel = TitleLabel("Settings", self.host)
        self.hostLayout.addWidget(self.titleLabel)
        self.hostLayout.addSpacing(6)

        self.hostLayout.addSpacing(24)
        self._setup_shortcuts_section()

        self.hostLayout.addSpacing(24)
        self._setup_library_section()

        self.hostLayout.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.scrollArea)

    def _setup_shortcuts_section(self) -> None:
        self._shortcutsCard = ExpandGroupSettingCard(
            FIF.CANCEL,
            "Shortcuts",
            "Configure keyboard shortcuts",
            parent=self.host,
        )
        self.hostLayout.addWidget(self._shortcutsCard)

        s = QSettings("Shortcuts")
        dflt_esc = QKeySequence(QKeySequence.StandardKey.Cancel).toString()
        dflt_find = QKeySequence(QKeySequence.StandardKey.Find).toString()

        self._escCard = PushSettingCard(
            "Change\u2026",
            FIF.CANCEL,
            "Go Back",
            s.value("goBack", dflt_esc),
            self._shortcutsCard,
        )
        self._escCard.clicked.connect(
            lambda: self._change_shortcut("goBack", self._escCard, dflt_esc)
        )
        self._shortcutsCard.addGroupWidget(self._escCard)

        self._findCard = PushSettingCard(
            "Change\u2026",
            FIF.SEARCH,
            "Focus Search",
            s.value("focusSearch", dflt_find),
            self._shortcutsCard,
        )
        self._findCard.clicked.connect(
            lambda: self._change_shortcut("focusSearch", self._findCard, dflt_find)
        )
        self._shortcutsCard.addGroupWidget(self._findCard)

    def _change_shortcut(self, key: str, card: SettingCard, default: str) -> None:
        s = QSettings("Shortcuts")
        current = s.value(key, default)
        dlg = _ShortcutDialog(current, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            seq = dlg.key_sequence()
            if seq:
                s.setValue(key, seq)
                card.setContent(seq)
                signalBus.shortcutsChanged.emit()

    def _setup_library_section(self) -> None:
        group = SettingCardGroup("Library", self.host)
        self.hostLayout.addWidget(group)

        self._foldersCard = FolderListSettingCard(
            cfg.localAnimeFolders,
            "Local Anime Folders",
            "Manage folders for local anime files",
            directory=QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.MusicLocation
            ),
            parent=group,
        )
        self._foldersCard.folderChanged.connect(self._on_folders_changed)
        group.addSettingCard(self._foldersCard)

        lib_path = library_path()
        self._pathCard = PushSettingCard(
            "Open Folder",
            FIF.FOLDER,
            "Library File",
            str(lib_path),
            group,
        )
        self._pathCard.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(lib_path.parent)))
        )
        group.addSettingCard(self._pathCard)

        self._loadCard = PushSettingCard(
            "Load File\u2026",
            FIF.DOWNLOAD,
            "Restore from File",
            "Load your library from a backup JSON file",
            group,
        )
        self._loadCard.clicked.connect(self._on_load_library)
        group.addSettingCard(self._loadCard)

    def _on_folders_changed(self, folders: list[str]) -> None:
        logger.info("Local anime folders changed: {}", folders)

    def _on_load_library(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Library",
            "",
            "JSON Files (*.json)",
        )
        if not path:
            return
        msgBox = MessageBox(
            "Replace Library?",
            "This will replace your entire library with the contents of the selected file.\n\n"
            "This cannot be undone. Continue?",
            self,
        )
        msgBox.yesSignal.connect(lambda: self._do_load_library(path))
        msgBox.exec()

    def _do_load_library(self, path: str) -> None:
        try:
            lib = get_library()
            count = lib.load_from(path)
            signalBus.libraryChanged.emit()
            logger.info("Library restored from {} ({} entries)", path, count)
            self._pathCard.setContent(str(library_path()))
        except Exception as e:
            logger.error("Failed to load library from {}: {}", path, e)

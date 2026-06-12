"""Cross-component signal bus."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    libraryChanged = pyqtSignal()
    libraryAdded = pyqtSignal(object)
    libraryRemoved = pyqtSignal(object)
    libraryFavoriteToggled = pyqtSignal(object, bool)
    libraryStatusChanged = pyqtSignal(object, str)
    openAnimeDetail = pyqtSignal(object)
    goBack = pyqtSignal()
    shortcutsChanged = pyqtSignal()


signalBus = SignalBus()

from __future__ import annotations

import hashlib
import time
import weakref
from pathlib import Path
from typing import Callable

from loguru import logger
from PyQt6.QtCore import QByteArray, QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from ..config.app_config import AppConfig


def cachedir() -> Path:
    path = AppConfig.cache_dir() / "images"
    path.mkdir(parents=True, exist_ok=True)
    return path


def hashurl(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def _validate_url(url: str) -> None:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")


class ImageLoader(QObject):
    loaded = pyqtSignal(str, QPixmap)
    failed = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._in_flight: dict[QNetworkReply, str] = {}
        self._pending: set[str] = set()
        self._callbacks: dict[str, list[weakref.WeakMethod]] = {}
        self._nam.finished.connect(self._on_finished)
        self._cache_dir = cachedir()
        self._evict_old()

    @staticmethod
    def _evict_old(max_age_days: int = 30) -> None:
        cache_dir = cachedir()
        now = time.time()
        cutoff = now - max_age_days * 86400
        for p in cache_dir.iterdir():
            if p.is_file() and p.stat().st_mtime < cutoff:
                try:
                    p.unlink()
                except OSError:
                    pass

    def load(self, url: str, callback: Callable | None = None) -> None:
        _validate_url(url)
        url = url.strip()
        if callback is not None:
            self._callbacks.setdefault(url, []).append(weakref.WeakMethod(callback))
        if url in self._pending:
            return
        cached = self._cache_path(url)
        if cached.exists():
            pix = QPixmap(str(cached))
            if not pix.isNull():
                self._emit_loaded(url, pix)
                logger.debug("Image cache hit: {}", url)
                return
        logger.debug("Image cache miss, fetching: {}", url)
        self._pending.add(url)
        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "anitrack/0.1")
        reply = self._nam.get(request)
        if reply is None:
            logger.error("Failed to create network request for: {}", url)
            self._pending.discard(url)
            self.failed.emit(url)
            return
        self._in_flight[reply] = url

    def _emit_loaded(self, url: str, pix: QPixmap) -> None:
        for ref in self._callbacks.pop(url, []):
            cb = ref()
            if cb is not None:
                cb(url, pix)
        self.loaded.emit(url, pix)

    def _on_finished(self, reply: QNetworkReply) -> None:
        url = self._in_flight.pop(reply, "")
        self._pending.discard(url)
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                logger.warning(
                    "Image download failed: {} (error {})", url, reply.error()
                )
                self.failed.emit(url)
                return
            data: QByteArray = reply.readAll()
        finally:
            reply.deleteLater()
        if not url:
            return
        pix = QPixmap()
        if not pix.loadFromData(data):
            logger.warning("Image decode failed: {}", url)
            self.failed.emit(url)
            return
        try:
            self._cache_path(url).write_bytes(data.data())
        except OSError as e:
            logger.warning("Image cache write failed: {} ({})", url, e)
        self._emit_loaded(url, pix)

    def _cache_path(self, url: str) -> Path:
        return self._cache_dir / hashurl(url)


_imageloader: ImageLoader | None = None


def image_loader() -> ImageLoader:
    global _imageloader
    if _imageloader is None:
        _imageloader = ImageLoader()
    return _imageloader


def rounded_pixmap(pix: QPixmap, radius: int) -> QPixmap:
    if pix.isNull():
        return pix
    out = QPixmap(pix.size())
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(0, 0, pix.width(), pix.height(), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pix)
    painter.end()
    return out


def placeholder_pixmap(width: int, height: int) -> QPixmap:
    img = QImage(width, height, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor(70, 70, 90, 80))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, width, height, 10, 10)
    painter.end()
    return QPixmap.fromImage(img)

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor
from .online import _thumb_data


def _cover_data(path):
    try:
        from mutagen import File as MF
        audio = MF(path)
        if audio is None:
            return None
        if getattr(audio, "pictures", None):
            return audio.pictures[0].data
        tags = getattr(audio, "tags", None) or {}
        return next((tags[k].data for k in tags if k.startswith("APIC")), None)
    except Exception:
        return None


def _pix_from_data(data):
    pix = QPixmap()
    return pix if data and pix.loadFromData(data) and not pix.isNull() else None


def _dominant_color(pix):
    if pix is None or pix.isNull():
        return None
    img = pix.scaled(16, 16, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).toImage()
    rs = gs = bs = wsum = prs = pgs = pbs = 0.0
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            w = (max(c.red(), c.green(), c.blue()) - min(c.red(), c.green(), c.blue())) / 255.0
            rs += c.red() * w
            gs += c.green() * w
            bs += c.blue() * w
            wsum += w
            prs += c.red()
            pgs += c.green()
            pbs += c.blue()
    if wsum < 1:
        rs, gs, bs, wsum = prs, pgs, pbs, img.width() * img.height()
    return (int(rs / wsum), int(gs / wsum), int(bs / wsum)) if wsum else None


class CoverDownloadWorker(QThread):
    done = Signal(bytes, str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        self.done.emit(_thumb_data(self.url), self.url)


class CoverLoader(QThread):
    done = Signal(int, bytes)

    def __init__(self, tracks):
        super().__init__()
        self.tracks = list(tracks)

    def run(self):
        for i, track in enumerate(self.tracks):
            if data := _cover_data(track["path"]):
                self.done.emit(i, data)


class CoverMixin:
    def _first_pix(self, paths):
        return next((pix for p in paths if p.exists() and not (pix := QPixmap(str(p))).isNull()), None)

    def _vortex_icon(self):
        if not hasattr(self, "_vortex_icon_cache"):
            pix = self._first_pix((self._icon_path, self._vortex_path))
            self._vortex_icon_cache = QIcon(pix) if pix is not None else QIcon()
        return self._vortex_icon_cache

    def _set_cover(self, path=None, thumb_url=None):
        pix = (thumb_url and _pix_from_data(_thumb_data(thumb_url))) or (path and _pix_from_data(_cover_data(path))) or self._first_pix((self._vortex_path, self._icon_path))
        if pix is None:
            return
        self._set_cover_pix(pix)

    def _set_cover_pix(self, pix):
        self.lbl_cover.setPixmap(pix.scaled(240, 240, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        s = max(self.lbl_big_cover.width() or 280, 544)
        big = pix.scaled(s, s, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        circle = QPixmap(s, s)
        circle.fill(QColor(0, 0, 0, 0))
        painter = QPainter(circle)
        painter.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath(); clip.addEllipse(0, 0, s, s)
        painter.setClipPath(clip)
        painter.drawPixmap((s - big.width()) // 2, (s - big.height()) // 2, big)
        painter.end()
        self._big_cover_pix = circle
        self.lbl_big_cover.setPixmap(circle)
        self._cover_color = _dominant_color(pix)
        if getattr(self, "is_fullscreen", False):
            self._apply_cover_glow()

    def _set_cover_async(self, thumb_url):
        if not thumb_url:
            self._set_cover(None, None)
            return
        self._cover_dl_url = thumb_url
        self._retire_thread("_cover_dl_thread")
        self._cover_dl_thread = CoverDownloadWorker(thumb_url)
        self._cover_dl_thread.done.connect(self._on_cover_dl_done)
        self._cover_dl_thread.start()

    def _on_cover_dl_done(self, data, url):
        if url != getattr(self, "_cover_dl_url", None):
            return
        pix = _pix_from_data(data)
        if pix is not None:
            self._set_cover_pix(pix)

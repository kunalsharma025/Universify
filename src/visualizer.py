from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QPainterPath
from PySide6.QtWidgets import QWidget
import math, random


class _WaveAnim(QWidget):
    def __init__(self, parent, bars, seed, a, b, f, floor):
        super().__init__(parent)
        self.bars, self.t, self.playing = bars, 0, False
        self._floor = floor
        random.seed(seed)
        self.base = [a + b * abs(math.sin(i * f)) * random.uniform(0.6, 1.0) for i in range(bars)]
        self.levels = [floor] * bars
        self.timer = QTimer(self)
        self.timer.setInterval(90)
        self.timer.timeout.connect(self._tick)

    def start(self):
        self.playing = True
        if not self.timer.isActive():
            self.timer.start()

    def stop(self):
        self.playing = False
        self.timer.stop()
        self.levels = [self._floor] * self.bars
        self.update()

    def _tick(self):
        if not self.playing:
            return
        self.t += 1
        self.levels = [max(self._floor, min(1.0, v * (0.75 + 0.25 * math.sin(self.t * 0.25 + i * 0.6)))) for i, v in enumerate(self.base)]
        self.update()


class WaveBar(_WaveAnim):
    def __init__(self, parent=None):
        super().__init__(parent, 80, 7, 0.25, 0.65, 0.7, 0.08)
        self.setFixedHeight(60)
        self.progress = 0.0

    def set_progress(self, frac):
        self.progress = max(0.0, min(1.0, frac))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h, step = self.width(), self.height(), self.width() / self.bars
        for i in range(self.bars):
            level = self.levels[i] if self.playing else self.base[i] * 0.5
            bh = max(4, level * (h - 8))
            col = QColor("#FFFFFF" if i < self.progress * self.bars else "#737373")
            painter.setPen(col); painter.setBrush(col)
            painter.drawRoundedRect(int(i * step + (step - 2) / 2), int((h - bh) / 2), 2, int(bh), 2, 2)


class CircleWaveCover(_WaveAnim):
    def __init__(self, parent=None, size=240):
        super().__init__(parent, 48, 11, 0.3, 0.7, 0.9, 0.1)
        self.setFixedSize(size, size)
        self._pix = QPixmap()

    def setPixmap(self, pix):
        self._pix = pix if pix is not None else QPixmap()
        self.update()

    def pixmap(self):
        return self._pix

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2
        ring_r, pic_r = r - 24, r - 28
        painter.setPen(QPen(QColor("#FFFFFF" if self.playing else "#737373"), 3, Qt.SolidLine, Qt.RoundCap))
        for i in range(self.bars):
            ang = math.radians(i * 360 / self.bars - 90)
            level = self.levels[i] if self.playing else 0.15
            length = 4 + level * 12
            c, s = math.cos(ang), math.sin(ang)
            x1, y1 = cx + c * ring_r, cy + s * ring_r
            x2, y2 = cx + c * (ring_r + length), cy + s * (ring_r + length)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        painter.setPen(QColor(255, 255, 255, 30))
        painter.setBrush(QColor(0, 0, 0))
        painter.drawEllipse(int(cx - pic_r), int(cy - pic_r), int(pic_r * 2), int(pic_r * 2))
        if not self._pix.isNull():
            clip = QPainterPath()
            clip.addEllipse(cx - pic_r, cy - pic_r, pic_r * 2, pic_r * 2)
            painter.setClipPath(clip)
            big = self._pix.scaled(int(pic_r * 2), int(pic_r * 2), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap(int(cx - big.width() / 2), int(cy - big.height() / 2), big)

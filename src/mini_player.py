from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSlider, QFrame
from .ui_controls import _icon_btn, draw_icon


def _fmt(ms):
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


_SLIDER = "QSlider::groove:horizontal { height:6px; background:rgba(255,255,255,0.2); border-radius:3px; } QSlider::handle:horizontal { width:%dpx; height:%dpx; margin:%dpx 0; background:#FFFFFF; border-radius:%dpx; }"
_TOP_BTN = "QPushButton { background:transparent; color:#FFFFFF; font-size:12px; border:none; } QPushButton:hover { background:#2E2E2E; border-radius:16px; }"
_TOP_BTN_ON = "QPushButton { background:#FFFFFF; color:#000000; font-size:12px; border:none; border-radius:16px; }"
_CLOSE_BTN = "QPushButton { background:transparent; color:#FFFFFF; font-size:13px; border:1px solid rgba(255,255,255,0.35); border-radius:15px; } QPushButton:hover { background:#2E2E2E; }"
_TIME = "font-size:12px; color:#B3B3B3; border:none;"


def _lbl(text, style):
    l = QLabel(text)
    l.setStyleSheet(style)
    return l


def _slider(size, margin, radius, maximum):
    s = QSlider(Qt.Horizontal); s.setStyleSheet(_SLIDER % (size, size, margin, radius)); s.setRange(0, maximum)
    return s


class MiniPlayer(QWidget):
    """Small floating player, like the picture. Drag it anywhere, it stays on top."""

    def __init__(self, player):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint)
        self.p = player
        self.setWindowIcon(player.windowIcon())
        self._pinned = False
        self.setFixedSize(600, 170)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent; color:#FFFFFF;")
        self._drag = None; self._playing = None; self._cover = None
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setStyleSheet("QFrame { background:#111111; border:1px solid rgba(255,255,255,0.18); border-radius:20px; }")
        outer.addWidget(card)
        root = QHBoxLayout(card); root.setContentsMargins(14, 14, 14, 14); root.setSpacing(14)
        self.cover = QLabel()
        self.cover.setFixedSize(120, 120); self.cover.setAlignment(Qt.AlignCenter)
        self.cover.setStyleSheet("border-radius:16px; background:#2E2E2E; border:none;")
        root.addWidget(self.cover)
        mid = QVBoxLayout(); mid.setSpacing(6)
        top = QHBoxLayout()
        self.title = _lbl("Pick a song", "font-size:18px; font-weight:bold; border:none;"); top.addWidget(self.title, 1)
        for name, text, tip, w, style, gap, fn in (
                ("btn_pin", "Pin", "Keep on top", 44, _TOP_BTN, 0, self.toggle_pin),
                ("btn_center", "Center", "Move to the center of the screen", 56, _TOP_BTN, 0, self.center_player),
                ("btn_expand", "⤢", "Back to full player", 32, _TOP_BTN, 0, self.expand),
                ("btn_close", "✕", "Back to full player", 30, _CLOSE_BTN, 18, self.expand)):
            if gap:
                top.addSpacing(gap)
            b = QPushButton(text)
            b.setToolTip(tip); b.setFixedSize(w, 32); b.setStyleSheet(style); b.clicked.connect(fn)
            if name == "btn_pin": self.btn_pin = b
            top.addWidget(b)
        mid.addLayout(top)
        self.artist = _lbl("", "font-size:14px; color:#B3B3B3; border:none;"); mid.addWidget(self.artist)
        prog = QHBoxLayout()
        self.lbl_left, self.lbl_right = _lbl("0:00", _TIME), _lbl("0:00", _TIME)
        self.seek = _slider(16, -5, 8, 1000)
        self.seek.sliderMoved.connect(self.p.on_seek)
        self.seek.installEventFilter(self)
        prog.addWidget(self.lbl_left); prog.addWidget(self.seek, 1); prog.addWidget(self.lbl_right)
        mid.addLayout(prog)
        ctrl = QHBoxLayout()
        ctrl.setAlignment(Qt.AlignLeft)
        for name, kind, color, big, fn in (
                ("btn_prev", "prev", "#FFFFFF", False, self.p.play_prev),
                ("btn_play", "play", "#000000", True, self.p.toggle_play),
                ("btn_next", "next", "#FFFFFF", False, self.p.play_next)):
            b = _icon_btn(kind, color, big=big); b.clicked.connect(fn)
            if name == "btn_play": self.btn_play = b
            ctrl.addWidget(b)
        self.volume = _slider(14, -4, 7, 100)
        self.volume.setValue(70); self.volume.setFixedWidth(100)
        self.volume.valueChanged.connect(lambda v: self.p.vlc.set_volume(v))
        ctrl.addWidget(self.volume)
        mid.addLayout(ctrl)
        root.addLayout(mid, 1)
        self.timer = QTimer(self); self.timer.setInterval(500)
        self.timer.timeout.connect(self.sync); self.timer.start()

    def eventFilter(self, obj, event):
        if obj is self.seek and event.type() == event.Type.MouseButtonPress:
            value = int(event.position().x() / max(1, self.seek.width()) * 1000)
            self.seek.setValue(value); self.p.on_seek(value); return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag is not None: self.move(event.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, event):
        self._drag = None

    def toggle_pin(self):
        self._pinned = not self._pinned
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint if self._pinned else self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()
        self.btn_pin.setStyleSheet(_TOP_BTN_ON if self._pinned else _TOP_BTN)

    def ensure_visible(self):
        if not any(s.availableGeometry().intersects(self.frameGeometry()) for s in QGuiApplication.screens()):
            self.center_player()

    def center_player(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2, screen.center().y() - self.height() // 2)

    def closeEvent(self, event):
        if getattr(self, "_quitting", False): event.accept()
        else: event.ignore(); self.expand()

    def mouseDoubleClickEvent(self, event):
        self.expand()

    def expand(self):
        self.hide(); self.p.show(); self.p.raise_(); self.p.activateWindow()

    def sync(self):
        p = self.p
        title, artist = (p.lbl_now.text().split(" - ", 1) + [""])[:2]
        if self.title.text() != title:
            self.title.setText(title)
        if self.artist.text() != artist:
            self.artist.setText(artist)
        pix = None
        for s in (getattr(p, "lbl_big_cover", None), getattr(p, "lbl_cover", None)):
            if s is not None:
                _px = s.pixmap()
                if _px is not None and not _px.isNull():
                    pix = _px
                    break
        if pix is not None and not pix.isNull() and pix.cacheKey() != self._cover:
            self._cover = pix.cacheKey()
            self.cover.setPixmap(pix.scaled(120, 120, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        length, pos = p.vlc.get_length(), p.vlc.get_time()
        if length > 0:
            self.seek.blockSignals(True)
            self.seek.setValue(int(pos * 1000 / length))
            self.seek.blockSignals(False)
        self.lbl_left.setText(_fmt(pos)); self.lbl_right.setText(_fmt(length))
        if p.volume.value() != self.volume.value(): self.volume.setValue(p.volume.value())
        if self._playing != p.is_playing:
            self._playing = p.is_playing; self.btn_play.setIcon(draw_icon("pause" if p.is_playing else "play", "#000000", 28))

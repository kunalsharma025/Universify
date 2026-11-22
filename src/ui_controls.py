from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPolygon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QSlider, QListWidget
from .config import TEXT, DIM
from .visualizer import WaveBar, CircleWaveCover


def _btn(bg, fg, size, radius, hover, pressed=None, extra="", hov="background"):
    r = f" border-radius:{radius}px;" if radius else ""
    return (f"QPushButton {{ background:{bg}; color:{fg}; font-size:{size}px;{extra}{r} }} QPushButton:hover {{ {hov}:{hover}; }}"
            + (f" QPushButton:pressed {{ background:{pressed}; }}" if pressed else ""))


def draw_icon(kind, color="#FFFFFF", size=28):
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QColor(color))
    painter.setBrush(QColor(color))
    s, c = size, size // 2
    if kind == "play":
        painter.drawPolygon(QPolygon([QPoint(s // 4, s // 6), QPoint(s // 4, 5 * s // 6), QPoint(5 * s // 6, c)]))
    elif kind == "pause":
        w = s // 6
        for x in (s // 4, s // 2 + w // 2):
            painter.drawRect(x, s // 6, w, 2 * s // 3)
    elif kind in ("prev", "next"):
        fwd = kind == "next"
        painter.drawRect(5 * s // 6 - s // 8 if fwd else s // 6, s // 6, s // 8, 2 * s // 3)
        tx, tip = (s // 6, 3 * s // 4) if fwd else (5 * s // 6, s // 4)
        painter.drawPolygon(QPolygon([QPoint(tx, s // 6), QPoint(tx, 5 * s // 6), QPoint(tip, c)]))
    painter.end()
    return QIcon(pm)


def _icon_btn(kind, color, size=28, big=False, style=None):
    sz = 32 if big else 28
    b = QPushButton()
    b.setIcon(draw_icon(kind, color, sz))
    b.setIconSize(QSize(sz, sz))
    b.setFixedSize(sz * 2, sz * 2)
    b.setStyleSheet(style or (_btn("#FFFFFF", "#000000", 32, 32, "#F0F0F0", "#D4D4D4") if big else _btn("#2E2E2E", "#FFFFFF", 28, 28, "#3A3A3A", "#4A4A4A")))
    return b


def _transport(style=None):
    return _icon_btn("prev", "#FFFFFF", 28, style=style), _icon_btn("play", "#000000", 32, big=True), _icon_btn("next", "#FFFFFF", 28, style=style)


def _text_btn(text, style, slot):
    b = QPushButton(text)
    b.setFixedHeight(36)
    b.setStyleSheet(style)
    b.clicked.connect(slot)
    return b


def build_left_rail(p):
    p.left_rail = left = QFrame()
    left.setFixedWidth(84)
    left.setStyleSheet("background: #121212; border-right: 1px solid rgba(255,255,255,0.08);")
    left_layout = QVBoxLayout(left)
    left_layout.setAlignment(Qt.AlignTop)
    left_layout.setContentsMargins(6, 10, 6, 10)
    p.lbl_dock_icon = QLabel()
    _ic = p._vortex_icon()
    if not _ic.isNull():
        p.lbl_dock_icon.setPixmap(_ic.pixmap(48, 48).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    p.lbl_dock_icon.setAlignment(Qt.AlignCenter)
    left_layout.addWidget(p.lbl_dock_icon)
    for attr, glyph, tip, name, idx in (("btn_vault", "⌂", "Local Vault", "Home", 0), ("btn_cinema", "▣", "Cinema / Video", "Cinema", 1),
                                        ("btn_online", "○", "Online Stream", "Online", 2), ("btn_ai", "✦", "AI Studio", "AI", 3),
                                        ("btn_fav", "♥", "Favourites", "Favs", 5)):
        b = QPushButton(glyph)
        b.setToolTip(tip)
        b.setFixedSize(56, 48)
        b.setStyleSheet(_btn("transparent", TEXT, 30, 24, "#2E2E2E", "#3A3A3A"))
        b.clicked.connect(lambda _=False, i=idx: p.show_page(i))
        setattr(p, attr, b)
        left_layout.addWidget(b, 0, Qt.AlignCenter)
        _nl = QLabel(name)
        _nl.setAlignment(Qt.AlignCenter)
        _nl.setStyleSheet(f"color:{DIM}; font-size:10px;")
        left_layout.addWidget(_nl)
    left_layout.addStretch()
    return left


def build_now_page(p):
    page = QWidget()
    page.setStyleSheet("background: qlineargradient(x1:0 y1:0 x2:0 y2:1, stop:0 #000000, stop:0.6 #121212, stop:1 #1E1E1E);")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 12)
    p.now_page_layout = layout
    nhead = QHBoxLayout()
    nhead.addWidget(_text_btn("‹ Back", "background:#2E2E2E; color:#FFFFFF; font-size:14px; padding:6px 14px; border-radius:18px;", p.toggle_now_playing))
    p.lbl_np_header = QLabel("Now Playing")
    p.lbl_np_header.setStyleSheet(f"color:{DIM}; font-size:15px; background:transparent;")
    nhead.addWidget(p.lbl_np_header)
    nhead.addStretch()
    pill = "background:#2E2E2E; color:#FFFFFF; font-size:15px; padding:8px 16px; border-radius:18px;"
    p.btn_mini_now = _text_btn("Mini", pill, p.show_mini_player)
    p.btn_mini_now.setToolTip("Mini player")
    nhead.addWidget(p.btn_mini_now)
    nhead.addSpacing(10)
    p.btn_full_now = _text_btn("⤢ Fullscreen", pill, p.toggle_fullscreen)
    p.btn_full_now.setToolTip("Fullscreen")
    nhead.addWidget(p.btn_full_now)
    layout.addLayout(nhead)
    layout.addStretch(1)
    body = QHBoxLayout()
    left = QVBoxLayout()
    p.lbl_big_cover = CircleWaveCover(size=300)
    left.addWidget(p.lbl_big_cover, 0, Qt.AlignCenter)
    left.addSpacing(18)
    p.lbl_big_title = QLabel("Pick a song")
    p.lbl_big_title.setStyleSheet("font-size:24px; font-weight:bold; background:transparent;")
    p.lbl_big_title.setWordWrap(True)
    p.lbl_big_title.setAlignment(Qt.AlignCenter)
    left.addWidget(p.lbl_big_title)
    p.lbl_big_artist = QLabel("")
    p.lbl_big_artist.setStyleSheet(f"color:{DIM}; font-size:18px; background:transparent;")
    p.lbl_big_artist.setAlignment(Qt.AlignCenter)
    p.lbl_big_artist.setVisible(False)
    left.addWidget(p.lbl_big_artist)
    p.btn_np_heart = QPushButton("♡")
    p.btn_np_heart.setFixedSize(40, 40)
    p.btn_np_heart.setStyleSheet(_btn("transparent", "#FFFFFF", 24, 0, "#D4D4D4", hov="color"))
    p.btn_np_heart.clicked.connect(p.toggle_heart)
    left.addWidget(p.btn_np_heart, 0, Qt.AlignCenter)
    p.wave = WaveBar()
    p.wave.setFixedHeight(60)
    left.addWidget(p.wave)
    body.addLayout(left, 1)
    right = QVBoxLayout()
    _up = QLabel("Up Next")
    _up.setStyleSheet("font-size:16px; font-weight:bold; background:transparent;")
    right.addWidget(_up)
    p.now_queue_list = QListWidget()
    p.now_queue_list.setFrameShape(QFrame.NoFrame)
    p.now_queue_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    p.now_queue_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    p.now_queue_list.setStyleSheet("QListWidget { background:transparent; border:none; font-size:14px; } QListWidget::item { background:transparent; border-radius:10px; padding:6px 10px; } QListWidget::item:hover { background: rgba(255,255,255,0.06); } QListWidget::item:selected { background: rgba(255,255,255,0.10); }")
    p.now_queue_list.itemClicked.connect(p.on_now_queue_clicked)
    right.addWidget(p.now_queue_list, 1)
    p.lbl_big_lyrics = QLabel("")
    p.lbl_big_lyrics.setStyleSheet("font-size:18px; font-weight:500; background:transparent;")
    p.lbl_big_lyrics.setWordWrap(True)
    p.lbl_big_lyrics.setAlignment(Qt.AlignCenter)
    right.addWidget(p.lbl_big_lyrics, 1)
    body.addLayout(right, 1)
    layout.addLayout(body, 1)
    np_time_row = QHBoxLayout()
    p.lbl_np_time_left, p.lbl_np_time, p.lbl_np_time_right = QLabel("0:00"), QLabel("0:00 / 0:00"), QLabel("0:00")
    for _l in (p.lbl_np_time_left, p.lbl_np_time, p.lbl_np_time_right):
        _l.setStyleSheet("background:transparent;")
    np_time_row.addWidget(p.lbl_np_time_left)
    np_time_row.addStretch()
    np_time_row.addWidget(p.lbl_np_time_right)
    layout.addLayout(np_time_row)
    now_bar = QFrame()
    now_bar.setStyleSheet("background:#1E1E1E; border-radius:20px;")
    now_layout = QVBoxLayout(now_bar)
    now_layout.setContentsMargins(16, 12, 16, 12)
    p.seek_np = QSlider(Qt.Horizontal)
    p.seek_np.setRange(0, 1000)
    p.seek_np.sliderMoved.connect(p.on_seek)
    now_layout.addWidget(p.seek_np)
    np_controls = QHBoxLayout()
    np_controls.setAlignment(Qt.AlignCenter)
    p.btn_np_shuffle, p.btn_np_repeat = QPushButton("⇄"), QPushButton("↻")
    for b in (p.btn_np_shuffle, p.btn_np_repeat):
        b.setFixedSize(40, 40)
        b.setStyleSheet(_btn("#2E2E2E", "#FFFFFF", 18, 20, "#3A3A3A"))
    p.btn_np_prev, p.btn_np_play, p.btn_np_next = _transport(_btn("transparent", "#FFFFFF", 28, 0, "#D4D4D4", hov="color"))
    for b in (p.btn_np_shuffle, p.btn_np_prev, p.btn_np_play, p.btn_np_next, p.btn_np_repeat):
        np_controls.addWidget(b)
    for b, slot in ((p.btn_np_shuffle, p.toggle_shuffle), (p.btn_np_prev, p.play_prev), (p.btn_np_play, p.toggle_play),
                    (p.btn_np_next, p.play_next), (p.btn_np_repeat, p.toggle_repeat)):
        b.clicked.connect(slot)
    now_layout.addLayout(np_controls)
    layout.addWidget(now_bar)
    return page


def build_dock(p):
    dock_wrap = QVBoxLayout()
    dock_wrap.setContentsMargins(12, 0, 12, 12)
    p.dock = dock = QFrame()
    dock.setFixedHeight(72)
    dock.setStyleSheet("background: #1E1E1E; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px;")
    dock_layout = QHBoxLayout(dock)
    p.btn_prev, p.btn_play, p.btn_next = _transport()
    for b, slot in ((p.btn_prev, p.play_prev), (p.btn_play, p.toggle_play), (p.btn_next, p.play_next)):
        dock_layout.addWidget(b)
        b.clicked.connect(slot)
    p.lbl_now = QLabel("Pick a song")
    p.lbl_now.mousePressEvent = lambda _e: p.toggle_now_playing()
    dock_layout.addWidget(p.lbl_now, 1)
    p.lbl_time = QLabel("0:00 / 0:00")
    dock_layout.addWidget(p.lbl_time)
    p.seek = QSlider(Qt.Horizontal)
    p.seek.setRange(0, 1000)
    p.seek.sliderMoved.connect(p.on_seek)
    dock_layout.addWidget(p.seek, 2)
    p.volume = QSlider(Qt.Horizontal)
    p.volume.setRange(0, 100)
    p.volume.setValue(70)
    p.volume.setFixedWidth(100)
    p.volume.valueChanged.connect(lambda v: p.vlc.set_volume(v))
    dock_layout.addWidget(p.volume)
    btn_mini = QPushButton("Mini")
    btn_mini.setToolTip("Mini player")
    btn_mini.setFixedSize(64, 48)
    btn_mini.setStyleSheet(_btn("#2E2E2E", "#FFFFFF", 14, 24, "#3A3A3A", extra=" font-weight:bold;"))
    btn_mini.clicked.connect(p.show_mini_player)
    dock_layout.addWidget(btn_mini)
    btn_expand = QPushButton("⤢")
    btn_expand.setToolTip("Expand now playing")
    btn_expand.clicked.connect(p.toggle_now_playing)
    dock_layout.addWidget(btn_expand)
    p.btn_subs = QPushButton("Subtitles")
    p.btn_subs.setToolTip("Add subtitles (.srt) for the video")
    p.btn_subs.setFixedHeight(36)
    p.btn_subs.setStyleSheet(_btn("#2E2E2E", "#FFFFFF", 14, 24, "#3A3A3A", extra=" font-weight:bold;"))
    p.btn_subs.clicked.connect(p.add_subtitles)
    p.btn_subs.setVisible(False)
    dock_layout.addWidget(p.btn_subs)
    p.btn_exit_full = QPushButton("✕ Exit")
    p.btn_exit_full.setToolTip("Exit fullscreen (Esc)")
    p.btn_exit_full.setFixedHeight(36)
    p.btn_exit_full.setStyleSheet(_btn("#FFFFFF", "#000000", 14, 24, "#F0F0F0", "#D4D4D4", extra=" font-weight:bold;"))
    p.btn_exit_full.clicked.connect(p.toggle_fullscreen)
    p.btn_exit_full.setVisible(False)
    dock_layout.addWidget(p.btn_exit_full)
    dock_wrap.addWidget(dock)
    return dock_wrap

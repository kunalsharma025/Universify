from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QLineEdit, QFrame
from .config import PANEL, CYAN, TEXT

W_BTN = "QPushButton { background:#FFFFFF; color:#000000; padding:8px 12px; border-radius:10px; } QPushButton:hover { background:#F0F0F0; } QPushButton:pressed { background:#D4D4D4; }"
BOX = f"background:{PANEL}; color:{TEXT}; padding:10px; border-radius:12px; border:none;"
CHART_BTN = f"QPushButton {{ background:{PANEL}; color:{TEXT}; padding:8px 10px; border-radius:12px; }} QPushButton:hover {{ background:#2E2E2E; }} QPushButton:pressed {{ background:#FFFFFF; color:#000000; }}"


def _page(title=""):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 16, 20, 12)
    if title:
        layout.addWidget(QLabel(title))
    return page, layout


def _btn(text, style, slot, pad=""):
    b = QPushButton(text)
    b.setStyleSheet(style.replace("8px 12px", pad) if pad else style)
    b.clicked.connect(slot)
    return b


def _row(layout, *widgets):
    row = QHBoxLayout()
    for w in widgets:
        row.addWidget(*w) if isinstance(w, tuple) else row.addWidget(w)
    layout.addLayout(row)
    return row


def _list(slot):
    w = QListWidget()
    w.setIconSize(QSize(64, 64))
    w.itemClicked.connect(slot)
    return w


def build_vault_page(p):
    page, layout = _page()
    btn_folder = _btn("＋ Add Folder", W_BTN, p.add_folder)
    _row(layout, QLabel("Local Vault"), btn_folder)
    now_card = QWidget()
    now_card.setStyleSheet(f"background:{PANEL}; border-radius:16px;")
    now_layout = QHBoxLayout(now_card)
    p.lbl_now_title = QLabel("Pick a song")
    p.lbl_now_title.setStyleSheet("font-size:16px; font-weight:bold; background:transparent;")
    p.lbl_quality = QLabel("")
    p.lbl_quality.setStyleSheet(f"color:{CYAN}; font-weight:bold; padding:6px 10px; border:1px solid {CYAN}; border-radius:12px;")
    now_layout.addWidget(p.lbl_now_title, 1)
    now_layout.addWidget(p.lbl_quality)
    layout.addWidget(now_card)
    p.track_list = _list(p.on_track_clicked)
    layout.addWidget(p.track_list)
    return page


def build_video_page(p):
    page, layout = _page()
    p.video_page_layout = layout
    p.video_header = QWidget()
    header = QHBoxLayout(p.video_header)
    header.setContentsMargins(0, 0, 0, 0)
    header.addWidget(QLabel("Cinema / Video"))
    header.addWidget(_btn("＋ Add Folder", W_BTN, p.add_video_folder))
    p.btn_full = QPushButton("⤢ Fullscreen  (F)")
    p.btn_full.clicked.connect(p.toggle_fullscreen)
    header.addWidget(p.btn_full)
    layout.addWidget(p.video_header)
    p.video_frame = QFrame()
    p.video_frame.setStyleSheet("background:#000000; border-radius:16px;")
    p.video_frame.installEventFilter(p)
    layout.addWidget(p.video_frame, 3)
    p.video_list = _list(p.on_video_clicked)
    layout.addWidget(p.video_list, 2)
    p.video_list.setVisible(False)
    p.video_empty = QWidget()
    empty_layout = QVBoxLayout(p.video_empty)
    empty_layout.setAlignment(Qt.AlignCenter)
    empty_label = QLabel("No videos yet")
    empty_label.setAlignment(Qt.AlignCenter)
    empty_label.setStyleSheet("font-size:18px; font-weight:bold; color:#FFFFFF; background:transparent;")
    empty_layout.addWidget(empty_label)
    empty_hint = QLabel("Add a folder of videos, or add one video file.")
    empty_hint.setAlignment(Qt.AlignCenter)
    empty_hint.setStyleSheet("font-size:13px; color:#B3B3B3; background:transparent;")
    empty_layout.addWidget(empty_hint)
    empty_btns = QHBoxLayout()
    empty_btns.setAlignment(Qt.AlignCenter)
    empty_btns.addWidget(_btn("＋ Add Folder", W_BTN, p.add_video_folder))
    empty_btns.addWidget(_btn("＋ Add Video", W_BTN, p.add_video))
    empty_layout.addLayout(empty_btns)
    layout.addWidget(p.video_empty, 2)
    return page


def build_online_page(p):
    page, layout = _page("Online Stream  •  YouTube Music (main)  •  JioSaavn (backup)  •  Audius (backup)")
    p.lbl_account = QLabel("Online - YouTube (main), JioSaavn, Audius")
    layout.addWidget(p.lbl_account)
    p.search_box = QLineEdit()
    p.search_box.setPlaceholderText("Search song - Hindi, Punjabi, Tamil, English...")
    p.search_box.setStyleSheet(BOX)
    p.search_box.returnPressed.connect(p.search_online)
    _row(layout, (p.search_box, 1), _btn("Search", W_BTN, p.search_online, "10px 16px"))
    chart_row = QHBoxLayout()
    for label, kind in (("Top India", "india"), ("Top World", "world"), ("Indie", "indie"), ("Trending", "trending"),
                        ("Spotify Top 50 India", "spotify_in"), ("Spotify Top 50 Global", "spotify_gl")):
        b = QPushButton(label)
        b.setStyleSheet(CHART_BTN)
        b.clicked.connect(lambda _=False, k=kind: p.load_chart(k))
        chart_row.addWidget(b)
    layout.addLayout(chart_row)
    p.online_list = _list(p.on_online_clicked)
    layout.addWidget(p.online_list)
    return page


def build_fav_page(p):
    page, layout = _page("Favourites  ♥")
    p.fav_list = _list(p.on_fav_clicked)
    layout.addWidget(p.fav_list)
    return page


def build_ai_page(p):
    page, layout = _page("AI Studio")
    p.ai_box = QLineEdit()
    p.ai_box.setPlaceholderText("Ask AI: play a happy Punjabi song, show lyrics...")
    p.ai_box.setStyleSheet(BOX)
    p.ai_box.returnPressed.connect(p.ask_ai)
    _row(layout, (p.ai_box, 1), _btn("Ask AI", W_BTN, p.ask_ai, "10px 16px"))
    p.lbl_ai = QLabel("Play a song, then ask AI for lyrics, BPM and mood.")
    p.lbl_ai.setWordWrap(True)
    layout.addWidget(p.lbl_ai)
    p.lbl_bpm = QLabel("BPM: -")
    layout.addWidget(p.lbl_bpm)
    layout.addWidget(_btn("Show AI info", W_BTN, p.show_ai_info, "10px"))
    layout.addStretch()
    return page

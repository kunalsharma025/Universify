import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton
from .config import TEXT
from .ui_pages import build_vault_page, build_video_page, build_online_page, build_ai_page, build_fav_page
from .ui_controls import build_left_rail, build_now_page, build_dock
from .ui_telemetry import build_inspector
from .cover import CoverMixin
from .player import VlcPlayer
from .ui_account import AccountMixin
from .mini_player import MiniPlayer
from .ui_online import OnlineMixin
from .ai_mixin import AiMixin
from .library import load_folders, load_last, load_favourites, load_video_folders
from .video_mixin import VideoMixin
from .fullscreen_mixin import FullscreenMixin
from .favourites_mixin import FavouritesMixin
from .playback_mixin import PlaybackMixin
from .tracks_mixin import TracksMixin


class UniversifyPlayer(QMainWindow, CoverMixin, AccountMixin, OnlineMixin, AiMixin, VideoMixin, FullscreenMixin, FavouritesMixin, PlaybackMixin, TracksMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universify")
        base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS") else Path(__file__).resolve().parent.parent
        self._icon_path, self._vortex_path = base / "assets" / "icon.png", base / "assets" / "vortex.jpg"
        pix = self._first_pix((self._icon_path, self._vortex_path)) or QPixmap()
        if not pix.isNull():
            self.setWindowIcon(QIcon(pix))
        self.resize(1180, 760)
        self.setMinimumSize(1000, 650)
        self.tracks, self._track_paths, self._info_cache = [], set(), {}
        self._search_thread = self._stream_thread = self._chart_thread = self._lyrics_thread = None
        self._lyrics_synced, self._lyrics_key, self._lyrics_idx = [], "", -2
        self._pending_online, self.current_index = None, -1
        self._favs = load_favourites()
        self._online_index, self._online_queue = -1, []
        self._online_queue_is_artist, self._online_from_search = False, False
        self._chart_kind, self._online_is_chart, self._autoplay_chart_first, self._stream_fail_streak = None, False, False, 0
        self._mode, self._ended, self._shuffle, self._repeat = "local", False, False, False
        self.is_fullscreen, self.page_before_now = False, 0
        self.online_results, self._chart_cache, self._search_cache, self._stream_cache = [], {}, {}, {}
        self.vlc, self.is_playing = VlcPlayer(), False
        root = QWidget()
        root.setObjectName("MainContainer")
        root.setStyleSheet(f"#MainContainer {{ background: qlineargradient(x1:0 y1:0 x2:1 y2:1, stop:0 #121212, stop:1 #1E1E1E); color:{TEXT}; }} QListWidget {{ background: transparent; border: none; color:#E2E8F0; font-size:13px; }} QListWidget::item {{ padding: 8px 12px; border-radius: 14px; margin-bottom: 6px; min-height: 64px; background: rgba(255,255,255,0.03); }} QListWidget::item:hover {{ background: rgba(255,255,255,0.06); }} QListWidget::item:selected {{ background: rgba(255,255,255,0.10); border-left: 3px solid #FFFFFF; color:#FFFFFF; }} QSlider::groove:horizontal {{ height: 6px; background: rgba(255,255,255,0.2); border-radius: 3px; }} QSlider::handle:horizontal {{ width: 16px; height: 16px; margin: -5px 0; background: #FFFFFF; border-radius: 8px; }}")
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0); top.setSpacing(0)
        main_layout.addLayout(top, 1)
        top.addWidget(build_left_rail(self))
        self.stack = QStackedWidget()
        top.addWidget(self.stack, 1)
        for build in (build_vault_page, build_video_page, build_online_page, build_ai_page, build_now_page, build_fav_page):
            self.stack.addWidget(build(self))
        top.addWidget(build_inspector(self))
        main_layout.addLayout(build_dock(self))
        self.btn_dock_toggle = QPushButton("⌄")
        self.btn_dock_toggle.setToolTip("Hide/show the control bar")
        self.btn_dock_toggle.setFixedHeight(22)
        self.btn_dock_toggle.setStyleSheet("QPushButton { background:#2E2E2E; color:#FFFFFF; font-size:14px; border-radius:11px; padding:0 14px; } QPushButton:hover { background:#3A3A3A; }")
        self.btn_dock_toggle.clicked.connect(self.toggle_dock_bar)
        self.btn_dock_toggle.setVisible(False)
        main_layout.addWidget(self.btn_dock_toggle, 0, Qt.AlignCenter)
        for s in (getattr(self, "seek", None), getattr(self, "seek_np", None)):
            if s is not None:
                s.installEventFilter(self)
        self.timer = QTimer(self)
        self.timer.setInterval(500); self.timer.timeout.connect(self.update_position); self.timer.start()
        self._mini, self._dead_threads, self._cover_color, self._stream_token, self._break_retry, self._break_retry_for = None, [], None, 0, 0, None
        self._refresh_fav_list()
        self._folders = load_folders()
        self._video_folders = load_video_folders()
        self._resume_pos, self._last_saved_pos, self._restore_paused = 0, 0, False
        self.load_saved_folders()
        self._restore_last()
        self.refresh_account_label()

    def _find_track(self, path):
        return next((i for i, tr in enumerate(self.tracks) if tr["path"] == path), -1)

    def _restore_last(self):
        last = load_last()
        if not last:
            return
        if last.get("kind") == "online" and last.get("track"):
            self._restore_paused, self._resume_pos = True, last["pos"]
            self.play_online(last["track"])
            if self._mode != "online":
                self._restore_paused, self._resume_pos = False, 0
            elif last["track"].get("artist"):
                self.search_box.setText(last["track"]["artist"].split(",")[0].strip())
                self._online_from_search = True
                self.search_online()
        elif last.get("kind") == "local" and self.tracks:
            idx = self._find_track(last["path"])
            if idx >= 0:
                self._restore_paused, self._resume_pos = True, last["pos"]
                self.vlc.set_volume(0)
                self.play_index(idx)

    def _stop_thread(self, name, wait=0):
        th = getattr(self, name, None)
        if th is not None and th.isRunning():
            th.quit()
            if wait:
                th.wait(wait)

    def _retire_thread(self, name):
        old = getattr(self, name, None)
        if old is not None and old.isRunning():
            self._dead_threads.append(old)
            old.finished.connect(lambda _o=old: self._dead_threads.remove(_o) if _o in self._dead_threads else None)
        setattr(self, name, None)

    def show_mini_player(self):
        if self._mini is None:
            self._mini = MiniPlayer(self)
            self._mini.move(self.x() + 100, self.y() + 100)
        self._mini.ensure_visible()
        try:
            self._mini.sync()
        except Exception:
            pass
        self._mini.show()
        self._mini.raise_(); self._mini.activateWindow()
        self.hide()

    def _set_slider(self, slider, value):
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)

    def closeEvent(self, event):
        self._save_pos(self.vlc.get_time())
        if getattr(self, "_mini", None) is not None:
            self._mini._quitting = True
            self._mini.close()
        for name in ("_cover_thread", "_search_thread", "_stream_thread", "_chart_thread", "_lyrics_thread", "_thumb_thread", "_cover_dl_thread"):
            self._stop_thread(name, wait=2000)
        for th in list(self._dead_threads):
            if th.isRunning():
                th.wait(2000)
        super().closeEvent(event)

    def show_page(self, index):
        if self.is_fullscreen:
            self.toggle_fullscreen()
        self.stack.setCurrentIndex(index)
        if hasattr(self, "btn_subs"):
            self.btn_subs.setVisible(index == 1)
        if index == 1:
            self._refresh_video_list()
            self.attach_video()

    def eventFilter(self, obj, event):
        if obj is self.video_frame and event.type() == event.Type.MouseButtonDblClick:
            self.toggle_fullscreen(); return True
        if obj in (getattr(self, "seek", None), getattr(self, "seek_np", None)) and event.type() == event.Type.MouseButtonPress:
            value = int(obj.minimum() + (obj.maximum() - obj.minimum()) * event.position().x() / max(1, obj.width()))
            obj.setValue(value)
            self.on_seek(value)
            return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F or (event.key() == Qt.Key_Escape and self.is_fullscreen):
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)


HybridPlayer = UniversifyPlayer

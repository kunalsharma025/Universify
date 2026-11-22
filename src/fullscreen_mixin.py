from PySide6.QtCore import Qt, QTimer

_NOW_BG = "background: qlineargradient(x1:0 y1:0 x2:0 y2:1, stop:0 #000000, stop:0.6 #121212, stop:1 #1E1E1E);"


class FullscreenMixin:
    def _sync_now_playing(self):
        for attr in ("wave", "lbl_cover", "lbl_big_cover"):
            w = getattr(self, attr, None)
            if w is not None and hasattr(w, "start"):
                w.start() if self.is_playing else w.stop()
        if hasattr(self, "btn_np_play"):
            self.btn_np_play.setIcon(self.btn_play.icon())
        if hasattr(self, "lbl_big_title"):
            title, _, artist = self.lbl_now.text().partition(" - ")
            self.lbl_big_title.setText(title)
            if hasattr(self, "lbl_big_artist"):
                self.lbl_big_artist.setText(artist)
                self.lbl_big_artist.setVisible(bool(artist))
        self._refresh_now_queue()
        if hasattr(self, "seek_np"):
            self._set_slider(self.seek_np, self.seek.value())
        if hasattr(self, "lbl_np_time"):
            self.lbl_np_time.setText(self.lbl_time.text())
        if hasattr(self, "lbl_np_time_left") and " / " in self.lbl_time.text():
            left, right = self.lbl_time.text().split(" / ", 1)
            self.lbl_np_time_left.setText(left)
            self.lbl_np_time_right.setText(right)

    def open_fullscreen_now(self):
        if self.stack.currentIndex() != 4:
            self.toggle_now_playing()
        if not self.is_fullscreen:
            self.toggle_fullscreen()

    def toggle_now_playing(self):
        if self.is_fullscreen:
            self.toggle_fullscreen()
        if self.stack.currentIndex() == 4:
            self.stack.setCurrentIndex(self.page_before_now)
        else:
            self.page_before_now = self.stack.currentIndex()
            self.lbl_big_title.setText(self.lbl_now.text())
            self.stack.setCurrentIndex(4)
            self._refresh_now_queue()
        if hasattr(self, "dock"):
            self.dock.show() if self.stack.currentIndex() != 4 else self.dock.hide()

    def _apply_cover_glow(self):
        page = self.stack.widget(4)
        c = getattr(self, "_cover_color", None)
        if c:
            r, g, b = c
            page.setStyleSheet(f"background: qradialgradient(cx:0.5 cy:0.32, radius:0.8, fx:0.5 fy:0.32, stop:0 rgba({r},{g},{b},0.45), stop:0.55 rgba({r},{g},{b},0.15), stop:1 #000000);")
        else:
            page.setStyleSheet(_NOW_BG)

    def _fullscreen_ui(self, on):
        size = 440 if on else 300
        if hasattr(self, "lbl_big_cover"):
            self.lbl_big_cover.setFixedSize(size, size)
        if hasattr(self, "wave"):
            self.wave.setFixedHeight(70 if on else 60)
        if hasattr(self, "lbl_big_title"):
            self.lbl_big_title.setAlignment(Qt.AlignCenter)
            self.lbl_big_title.setStyleSheet("font-size:32px; font-weight:bold; background:transparent;" if on else "font-size:24px; font-weight:bold; background:transparent;")
        if hasattr(self, "lbl_big_lyrics"):
            self.lbl_big_lyrics.setStyleSheet("font-size:22px; font-weight:500; line-height:1.5; background:transparent;" if on else "font-size:18px; font-weight:500; background:transparent;")
            self.lbl_big_lyrics.setMaximumHeight(200 if on else 110)
        if hasattr(self, "now_page_layout"):
            self.now_page_layout.setContentsMargins(20, 16, 20, 0 if on else 12)
        self._apply_cover_glow() if on else self.stack.widget(4).setStyleSheet(_NOW_BG)
        is_cinema = self.stack.currentIndex() == 1
        for w in (self.left_rail, self.inspector):
            w.hide() if on else w.show()
        if on and is_cinema:
            self.dock.show()
        elif on:
            self.dock.hide()
        else:
            self.dock.show()
        if hasattr(self, "btn_exit_full"):
            self.btn_exit_full.setVisible(on)
        if hasattr(self, "btn_dock_toggle"):
            self.btn_dock_toggle.setVisible(on and is_cinema)
            if on and is_cinema:
                self.btn_dock_toggle.setText("⌄")
        self.btn_full.setText("⤢ Exit Fullscreen  (Esc)" if on else "⤢ Fullscreen  (F)")
        if hasattr(self, "btn_full_now"):
            self.btn_full_now.setText("✕ Exit Fullscreen" if on else "⤢ Fullscreen")
        if hasattr(self, "video_header"):
            self.video_header.setVisible(not (on and is_cinema))
        if hasattr(self, "video_list"):
            self.video_list.setVisible(not (on and is_cinema))
        if hasattr(self, "video_page_layout"):
            self.video_page_layout.setContentsMargins(0, 0, 0, 0) if (on and is_cinema) else self.video_page_layout.setContentsMargins(20, 16, 20, 12)
        if hasattr(self, "video_frame"):
            self.video_frame.setStyleSheet("background:#000000; border-radius:0px;" if (on and is_cinema) else "background:#000000; border-radius:16px;")
        self._sync_now_playing()

    def toggle_fullscreen(self):
        if not self.is_fullscreen:
            self._fullscreen_ui(True); self.showFullScreen(); self.is_fullscreen = True
        else:
            self.showNormal(); self._fullscreen_ui(False); self.is_fullscreen = False
        QTimer.singleShot(100, self.attach_video)

import random
from .config import VIDEO_EXTS
from .library import save_last, save_online
from .ui_controls import draw_icon
from .ui_telemetry import set_online_duration


def _fmt(ms):
    return f"{int(ms // 60000)}:{int((ms // 1000) % 60):02d}"


class PlaybackMixin:
    def _pause(self):
        self.vlc.set_paused(True)
        self.is_playing = False
        self._set_play_icon(False)

    def _set_play_icon(self, playing):
        icon = draw_icon("pause" if playing else "play", "#000000", 32)
        self.btn_play.setIcon(icon)
        if hasattr(self, "btn_np_play"):
            self.btn_np_play.setIcon(icon)

    def play_index(self, index):
        if not (0 <= index < len(self.tracks)):
            return
        self._mode, self._ended, self.current_index = "local", False, index
        self._loading_stream = False
        track = self.tracks[index]
        self.show_inspector(track["path"])
        if track["path"].lower().endswith(VIDEO_EXTS):
            self.show_page(1)
        self.vlc.play_path(track["path"])
        self.is_playing = True
        self._set_play_icon(True)
        self.lbl_now.setText(f"{track['title']} - {track['artist']}" if track["artist"] else track["title"]); self.lbl_big_title.setText(self.lbl_now.text())
        self._refresh_heart()
        self._load_lyrics(track["title"], track["artist"])

    def _now_queue(self):
        if self._mode == "online":
            return self._online_queue if getattr(self, "_online_queue", None) else self.online_results
        return self.tracks

    def _refresh_now_queue(self):
        if not hasattr(self, "now_queue_list"):
            return
        q = self._now_queue()
        cur = self._online_index if self._mode == "online" else self.current_index
        key = (tuple((r.get("videoId") or r.get("path", "")) for r in q), cur, self._mode)
        if getattr(self, "_now_queue_key", None) == key:
            return
        self._now_queue_key = key
        self.now_queue_list.clear()
        for r in q:
            title, artist = r.get("title", ""), r.get("artist", "")
            self.now_queue_list.addItem(f"{title}\n{artist}" if artist else title)
        if 0 <= cur < len(q):
            self.now_queue_list.setCurrentRow(cur)

    def on_now_queue_clicked(self, item):
        q = self._now_queue()
        idx = self.now_queue_list.row(item)
        if 0 <= idx < len(q):
            if self._mode == "online":
                self.play_online(q[idx])
            else:
                self.play_index(idx)

    def _stop_at_end(self):
        self._pause()
        artist = (self._pending_online or {}).get("artist", "")
        self.lbl_now.setText(f"Finished {artist}'s songs" if artist else "Finished")
        self._sync_now_playing()

    def _online_step(self, step):
        q = self._now_queue()
        if not q:
            return 0
        if self._shuffle:
            self.play_online(random.choice(q))
            return 1
        idx = self._online_index
        if idx < 0:
            idx = 0 if step > 0 else len(q) - 1
        elif step > 0 and idx >= len(q) - 1:
            if getattr(self, "_online_queue_is_artist", False):
                self._stop_at_end()
                return -1
            if getattr(self, "_online_is_chart", False):
                self._chain_next_chart()
                return 1
            idx = 0
        else:
            idx = (idx + step) % len(q)
        self.play_online(q[idx])
        return 1

    def play_next_random(self):
        if self._mode == "online":
            if self._online_step(1) == 0: self._replay_current()
        elif self._is_video_current():
            if not self._play_next_video(1):
                self._pause()
        elif self.tracks:
            self.play_index(random.randrange(len(self.tracks)))

    def toggle_play(self):
        if getattr(self, "_restore_paused", False):
            self._restore_paused = False
            self._resume_pos = 0
            self.vlc.set_volume(self.volume.value())
        if not (self._mode == "online" and self._pending_online) and self.current_index == -1 and self.tracks:
            self.play_index(0)
            return
        self.is_playing = not self.vlc.is_playing()
        self.vlc.set_paused(not self.is_playing)
        self._set_play_icon(self.is_playing)
        self._sync_now_playing()

    def _toggle_flag(self, attr, btn_attr):
        val = not getattr(self, attr)
        setattr(self, attr, val)
        btn = getattr(self, btn_attr, None)
        if btn is not None:
            btn.setStyleSheet(f"QPushButton {{ background: {'#FFFFFF' if val else '#2E2E2E'}; color:{'#000000' if val else '#FFFFFF'}; font-size:22px; border-radius:24px; }}")

    def toggle_shuffle(self):
        self._toggle_flag("_shuffle", "btn_np_shuffle")

    def toggle_repeat(self):
        self._toggle_flag("_repeat", "btn_np_repeat")

    def _advance(self):
        self._ended = True
        self._replay_current() if self._repeat else self.play_next_random()

    def _replay_current(self):
        if self._mode == "online" and self._pending_online:
            self.play_online(self._pending_online)
        elif 0 <= self.current_index < len(self.tracks):
            self.play_index(self.current_index)

    def play_next(self):
        if self._repeat:
            self._replay_current()
        elif self._mode == "online":
            if self._online_step(1) == -1:
                q = self._now_queue()
                if q:
                    self._online_index = -1
                    self._online_step(1)
        elif self._is_video_current():
            if not self._play_next_video(1):
                self._pause()
        elif self._shuffle:
            self.play_next_random()
        elif self.tracks:
            self.play_index((self.current_index + 1) % len(self.tracks))

    def play_prev(self):
        if self._mode == "online" and self._now_queue(): self._online_step(-1)
        elif self._is_video_current():
            self._play_next_video(-1)
        elif self.tracks: self.play_index((self.current_index - 1) % len(self.tracks))

    def on_seek(self, value):
        length = self.vlc.get_length()
        if length > 0:
            self.vlc.set_time(int(length * value / 1000))

    def _save_pos(self, pos):
        self._last_saved_pos = pos
        if self._mode == "online" and self._pending_online:
            save_online(self._pending_online, pos)
        elif 0 <= self.current_index < len(self.tracks):
            save_last(self.tracks[self.current_index]["path"], pos)

    def update_position(self):
        length, pos = self.vlc.get_length(), self.vlc.get_time()
        if self.is_playing and not self._ended and not getattr(self, "_loading_stream", False) and self.vlc.is_ended():
            if self._mode == "online" and not (length > 0 and pos > 0):
                vid = (getattr(self, "_pending_online", None) or {}).get("videoId", "")
                tried = getattr(self, "_backup_tried", set())
                if vid and vid not in tried:
                    self._backup_tried = tried
                    tried.add(vid)
                    if self._retry_with_backup():
                        return
                self._ended = True
                self.is_playing = False
                self._set_play_icon(False)
                self.lbl_now.setText("That song wouldn't play - pick another one.")
                return
            if (self._mode == "online" and length > 0 and pos < length * 0.9
                    and getattr(self, "_break_retry", 0) < 1):
                self._break_retry = getattr(self, "_break_retry", 0) + 1
                self.lbl_now.setText("Stream broke, trying the same song again...")
                self._replay_current()
                return
            self._advance()
            return
        if getattr(self, "_resume_pos", 0) and length > 0:
            self.vlc.set_time(min(self._resume_pos, length - 1000))
            self._resume_pos = 0
            if getattr(self, "_restore_paused", False):
                self._restore_paused = False
                self._pause()
                self.vlc.set_volume(self.volume.value())
                self._sync_now_playing()
        if self.is_playing and pos > 0 and pos - self._last_saved_pos >= 10000:
            self._save_pos(pos)
        if length > 0:
            self._set_slider(self.seek, int(pos * 1000 / length))
            self.lbl_time.setText(f"{_fmt(pos)} / {_fmt(length)}")
            if hasattr(self, "wave"):
                self.wave.set_progress(pos / length)
            if self._mode == "online":
                set_online_duration(self, length)
            self._sync_now_playing()
            if pos >= length - 1500 and not self._ended and not getattr(self, "_loading_stream", False):
                self._advance()
        if self.is_playing and pos > 0:
            self._update_lyrics_line(pos)

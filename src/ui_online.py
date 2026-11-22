import time
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QListWidgetItem, QMessageBox
from .online import SearchWorker, StreamWorker, ChartWorker, ThumbWorker, is_offline, OFFLINE_MSG
from .ui_telemetry import set_online_telemetry


def _pix(data):
    pix = QPixmap()
    return pix if data and pix.loadFromData(data) and not pix.isNull() else None


def _alnum(s, space=False):
    return "".join(c for c in (s or "").lower() if c.isalnum() or (space and c.isspace()))


def _same_artist(a, b):
    a, b = _alnum(a), _alnum(b)
    return bool(a and b) and (a == b or a in b or b in a)


def _fresh(cached, ttl=1800):
    return cached and time.time() - cached[0] < ttl


CHART_KINDS = ["india", "world", "indie", "trending", "spotify_in", "spotify_gl"]
_EN_CHARTS = ["world", "spotify_gl"]
_IN_CHARTS = ["india", "indie", "trending", "spotify_in"]
CHART_LABELS = {"india": "Top India", "world": "Top World", "indie": "Indie", "trending": "Trending", "spotify_in": "Spotify Top 50 India", "spotify_gl": "Spotify Top 50 Global"}


def _clean_key(title, artist):
    t = _alnum(title, True).split("(")[0].split("[")[0]
    return (" ".join(t.split()), " ".join(_alnum((artist or "").split(",")[0], True).split()))


def _dedup(results):
    seen, out = set(), []
    for r in results:
        if (key := _clean_key(r.get("title", ""), r.get("artist", "")))[0] and key not in seen:
            seen.add(key); out.append(r)
    return out


def _apply_thumb(item, data):
    if (pix := _pix(data or b"")) is not None:
        item.setIcon(QIcon(pix))


def _online_label(r):
    suffix = f"  ({r['source'].title()})" if r.get("source") in ("saavn", "audius") else ""
    return r["title"] if not r.get("artist") else f"{r['title']}{suffix}\n{r['artist']}"


class OnlineMixin:
    def _start_thread(self, attr, worker, done, failed=None):
        setattr(self, attr, worker)
        worker.done.connect(done)
        if failed is not None:
            worker.failed.connect(failed)
        worker.start()

    def _build_online_queue(self, cur, results):
        if getattr(self, "_online_from_search", False) and cur and cur.get("artist"):
            same = [r for r in results if _same_artist(r.get("artist", ""), cur.get("artist", ""))]
            self._online_queue_is_artist = len(same) > 1
            self._online_queue = same if self._online_queue_is_artist else list(results)
        else:
            self._online_queue, self._online_queue_is_artist = list(results), False
        self._online_index = next((i for i, r in enumerate(self._online_queue) if cur and (r is cur or (r.get("videoId"), r.get("source")) == (cur.get("videoId"), cur.get("source")))), -1)

    def _online_ok(self):
        if is_offline():
            self.online_list.clear(); self.online_list.addItem(OFFLINE_MSG)
            return False
        return True

    def search_online(self, from_chart=False):
        if not self._online_ok():
            return
        query = self.search_box.text().strip()
        if not query or (self._search_thread and self._search_thread.isRunning()):
            return
        if not from_chart:
            self._chart_kind = None
        if _fresh(self._search_cache.get(query.lower())):
            self._on_search_done(self._search_cache[query.lower()][1])
            return
        self._online_from_search = not from_chart
        self._mode = "online"
        self.online_list.clear(); self.online_results = []
        self.online_list.addItem("Searching...")
        self._start_thread("_search_thread", SearchWorker(query), self._on_search_done, self._on_search_failed)

    def load_chart(self, kind):
        if not self._online_ok():
            return
        self._chart_kind = kind
        if _fresh(self._chart_cache.get(kind)):
            self._on_chart_done(self._chart_cache[kind][1], kind)
            return
        if kind.startswith("spotify"):
            self.search_box.setText("Top 50 India" if kind == "spotify_in" else "Top 50 Global")
            self.search_online(from_chart=True)
            return
        self._online_from_search = False
        if self._chart_thread and self._chart_thread.isRunning():
            return
        self._mode = "online"
        self.online_list.clear()
        self.online_list.addItem("Loading chart...")
        self._start_thread("_chart_thread", ChartWorker(kind), self._on_chart_done, self._on_search_failed)

    def _on_chart_done(self, results, kind):
        self._chart_cache[kind] = (time.time(), results); self._chart_kind = kind
        self._on_search_done(results)

    def _chain_next_chart(self):
        cur = getattr(self, "_chart_kind", None)
        group = _EN_CHARTS if cur in _EN_CHARTS else _IN_CHARTS if cur in _IN_CHARTS else CHART_KINDS
        nxt = group[(group.index(cur) + 1) % len(group)] if cur in group else "india"
        self._autoplay_chart_first = True
        self.lbl_now.setText(f"Loading {CHART_LABELS[nxt]}...")
        self.load_chart(nxt)

    def _on_search_done(self, results):
        results = _dedup(results)
        self._online_is_chart = getattr(self, "_chart_kind", None) is not None
        q = self.search_box.text().strip().lower()
        if getattr(self, "_online_from_search", False) and q:
            self._search_cache[q] = (time.time(), results)
        self.online_list.clear(); self.online_results = results
        self._build_online_queue(getattr(self, "_pending_online", None), results)
        self._retire_thread("_thumb_thread")
        self._start_thread("_thumb_thread", ThumbWorker(results), self._on_thumbs_done)
        self.online_list.setUpdatesEnabled(False)
        for r in results:
            item = QListWidgetItem(_online_label(r)); _apply_thumb(item, r.get("thumb_data")); item.setSizeHint(QSize(0, 72)); self.online_list.addItem(item)
        self.online_list.setUpdatesEnabled(True)
        if not results:
            self.online_list.addItem("No results. Try JioSaavn backup next.")
        if getattr(self, "_autoplay_chart_first", False) and getattr(self, "_online_is_chart", False) and results:
            self._autoplay_chart_first = False
            self.play_online(results[0])

    def _on_thumbs_done(self, results):
        self.online_results = results
        for i, r in enumerate(results[:self.online_list.count()]): _apply_thumb(self.online_list.item(i), r.get("thumb_data"))

    def _on_search_failed(self, err):
        self.online_list.clear()
        self.online_list.addItem(f"YouTube search failed: {err}")
        self.online_list.addItem("Your local songs still work - open Local Vault from the left.")

    def on_online_clicked(self, item):
        index = self.online_list.row(item)
        if 0 <= index < len(self.online_results):
            self.play_online(self.online_results[index])

    on_online_double_clicked = on_online_clicked

    def play_online(self, track):
        if is_offline():
            QMessageBox.information(self, "Offline", OFFLINE_MSG)
            return
        vid = track.get("videoId", "")
        if not vid:
            return
        if vid != getattr(self, "_break_retry_for", None):
            self._break_retry = 0; self._break_retry_for = vid
        self._backup_tried = getattr(self, "_backup_tried", set())
        self._backup_tried.discard(vid)
        self._stream_token = getattr(self, "_stream_token", 0) + 1
        self._retire_thread("_stream_thread")
        self._mode = "online"
        self._pending_online = track
        self._build_online_queue(track, self.online_results)
        self._ended = False
        self._loading_stream = True
        self.lbl_now.setText("Loading stream...")
        cached = self._stream_cache.get(vid)
        if _fresh(cached, 1200):
            self._on_stream_done(cached[1], cached[2], cached[3], self._stream_token)
            return
        if (pix := _pix(track.get("thumb_data") or b"")) is not None:
            self.lbl_cover.setPixmap(pix.scaled(240, 240, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        self._start_thread("_stream_thread", StreamWorker(vid, track, self._stream_token), self._on_stream_done, self._on_stream_failed)

    def _retry_with_backup(self):
        track = getattr(self, "_pending_online", None)
        if not track:
            return False
        vid = track.get("videoId", "")
        if not vid:
            return False
        self._stream_token = getattr(self, "_stream_token", 0) + 1
        self._retire_thread("_stream_thread")
        self._loading_stream = True
        self.lbl_now.setText("YouTube refused that link - trying JioSaavn...")
        self._start_thread("_stream_thread", StreamWorker(vid, track, self._stream_token, backup_only=True), self._on_stream_done, self._on_stream_failed)
        return True

    def _on_stream_done(self, url, abr=0, asr=0, token=0):
        if token != getattr(self, "_stream_token", 0):
            return
        if not url or not self._pending_online:
            return
        track = self._pending_online
        self._stream_fail_streak = 0
        self._loading_stream = False
        self._stream_cache[track.get("videoId", "")] = (time.time(), url, abr, asr)
        self._ended = False
        if getattr(self, "_restore_paused", False):
            self.vlc.set_volume(0)
        self.vlc.play_url(url)
        self.is_playing = True
        self._set_play_icon(True)
        title = f"{track['title']} - {track['artist']}" if track["artist"] else track["title"]
        for lbl in (self.lbl_now, self.lbl_now_title, self.lbl_big_title):
            lbl.setText(title)
        self._load_lyrics(track["title"], track["artist"])
        self._refresh_heart()
        set_online_telemetry(self, track, abr, asr)
        if track.get("source") == "saavn":
            self.lbl_quality.setText("JIOSAAVN 320" if track.get("is_320") else "JIOSAAVN")
        self._sync_now_playing()
        self._set_cover_async(track.get("thumb_big", "") or track.get("thumb", ""))

    def _on_stream_failed(self, err, token=0):
        if token != getattr(self, "_stream_token", 0):
            return
        self._retire_thread("_stream_thread")
        self._loading_stream = False
        if getattr(self, "_restore_paused", False):
            self._restore_paused = False
            self.lbl_now.setText("Couldn't play the last song - pick one from the list.")
            return
        streak = self._stream_fail_streak = getattr(self, "_stream_fail_streak", 0) + 1
        if self._mode == "online" and self.online_results and streak < len(self.online_results):
            self.lbl_now.setText("That song is blocked, trying the next one...")
            self._online_step(1)
            return
        is_off = "offline" in str(err).lower()
        msg = OFFLINE_MSG if is_off else "YouTube blocked this song (it thinks it is a bot). Try again in a bit, or play a local song - JioSaavn backup will try next time."
        QMessageBox.information(self, "Offline" if is_off else "Play failed",
                                msg + "\n\nYour local songs still work - open Local Vault.")

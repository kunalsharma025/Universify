from PySide6.QtCore import QSize
from PySide6.QtWidgets import QListWidgetItem
from .library import save_favourites


class FavouritesMixin:
    def _fav_key(self):
        if self._mode == "online" and self._pending_online:
            t = self._pending_online
            d = {k: t.get(k, "") for k in ("videoId", "title", "artist", "enc", "thumb", "thumb_big")}
            d.update(kind="online", source=t.get("source", "youtube"), is_320=bool(t.get("is_320", True)))
            return d
        if 0 <= self.current_index < len(self.tracks):
            tr = self.tracks[self.current_index]
            return {"kind": "local", "path": tr["path"], "title": tr["title"], "artist": tr["artist"]}
        return None

    def _fav_id(self, fav):
        return ("local:" + fav["path"]) if fav["kind"] == "local" else (fav["source"] + ":" + fav["videoId"])

    def _refresh_heart(self):
        if not hasattr(self, "btn_np_heart"):
            return
        fav = self._fav_key()
        want = "♥" if fav and any(self._fav_id(f) == self._fav_id(fav) for f in self._favs) else "♡"
        if self.btn_np_heart.text() != want:
            self.btn_np_heart.setText(want)

    def toggle_heart(self):
        fav = self._fav_key()
        if not fav:
            return
        fid = self._fav_id(fav)
        if any(self._fav_id(f) == fid for f in self._favs):
            self._favs = [f for f in self._favs if self._fav_id(f) != fid]
        else:
            self._favs.append(fav)
        save_favourites(self._favs)
        self._refresh_heart()
        self._refresh_fav_list()

    def _refresh_fav_list(self):
        if not hasattr(self, "fav_list"):
            return
        self.fav_list.clear()
        for f in self._favs:
            item = QListWidgetItem(f["title"] + ("\n" + f["artist"] if f.get("artist") else ""))
            item.setSizeHint(QSize(0, 72))
            self.fav_list.addItem(item)

    def on_fav_clicked(self, item):
        row = self.fav_list.row(item)
        if not (0 <= row < len(self._favs)):
            return
        f = self._favs[row]
        if f["kind"] == "local":
            idx = self._find_track(f["path"])
            if idx >= 0:
                self.play_index(idx)
            return
        from .online import _track
        self.show_page(2)
        self.play_online(_track(**{k: f.get(k, "") for k in ("videoId", "title", "artist", "source", "enc", "thumb", "thumb_big")}, is_320=f.get("is_320", True)))

from pathlib import Path
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QFileDialog, QListWidgetItem, QMessageBox
from .config import VIDEO_EXTS
from .cover import CoverLoader
from .inspector import inspect_audio
from .library import load_folders, save_folders
from .scanner import scan_folder
from .ui_telemetry import set_local_telemetry


class TracksMixin:
    def _add_items(self, files, video=False):
        self.track_list.setUpdatesEnabled(False)
        for full in files:
            if full in self._track_paths:
                continue
            self._track_paths.add(full)
            self.tracks.append({"path": full, "title": Path(full).stem, "artist": ""})
            item = QListWidgetItem(Path(full).stem)
            if video:
                item.setIcon(self._vortex_icon())
            item.setSizeHint(QSize(0, 64 if video else 72))
            self.track_list.addItem(item)
        self.track_list.setUpdatesEnabled(True)

    def get_info(self, path):
        if path not in self._info_cache:
            self._info_cache[path] = inspect_audio(path)
        return self._info_cache[path]

    def _add_new(self, new):
        if new:
            self._add_items([full for full, _ in new]); self._start_cover_loader()

    def load_saved_folders(self):
        for folder in self._folders:
            self._add_new(scan_folder(folder, self._track_paths))
        for folder in getattr(self, "_video_folders", []):
            vids = [(full, stem) for full, stem in scan_folder(folder, self._track_paths) if full.lower().endswith(VIDEO_EXTS)]
            if vids:
                self._add_items([full for full, _ in vids], video=True)
        self._start_cover_loader()

    def _start_cover_loader(self):
        th = getattr(self, "_cover_thread", None)
        if not self.tracks:
            return
        if th is not None and th.isRunning():
            self._cover_restart = True
            return
        try:
            self._cover_thread = CoverLoader(self.tracks)
            self._cover_thread.done.connect(self._on_cover_loaded)
            self._cover_thread.finished.connect(self._on_cover_loader_done)
            self._cover_thread.start()
        except Exception:
            pass

    def _on_cover_loader_done(self):
        if getattr(self, "_cover_restart", False):
            self._cover_restart = False
            self._start_cover_loader()

    def _on_cover_loaded(self, path, data):
        pix = QPixmap()
        row = self._find_track(path)
        if row >= 0 and pix.loadFromData(data) and not pix.isNull():
            self.track_list.item(row).setIcon(QIcon(pix))

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose music folder")
        if not folder:
            return
        new = scan_folder(folder, self._track_paths)
        if not new:
            if folder not in self._folders:
                QMessageBox.information(self, "No files", "No audio/video files found in that folder.")
            return
        self._add_new(new)
        if folder not in self._folders:
            self._folders.append(folder); save_folders(self._folders)

    def on_track_clicked(self, item):
        self.play_index(self.track_list.row(item))

    def show_inspector(self, path):
        info = self.get_info(path)
        self._set_cover(path, None)
        row = self._find_track(path)
        if row >= 0:
            self.tracks[row].update(title=info["title"], artist=info["artist"])
            item = self.track_list.item(row)
            if item:
                item.setText(f"{info['title']}\n{info['artist']}" if info["artist"] else info["title"])
                cp = self.lbl_cover.pixmap()
                if cp is not None and not cp.isNull():
                    item.setIcon(QIcon(cp))
        set_local_telemetry(self, info)

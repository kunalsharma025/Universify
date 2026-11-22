from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QListWidgetItem, QMessageBox
from .config import VIDEO_EXTS
from .library import save_video_folders
from .scanner import scan_folder


class VideoMixin:
    def attach_video(self):
        try:
            wid = int(self.video_frame.winId())
            if wid:
                self.vlc.attach_video(wid)
        except Exception:
            pass

    def add_video(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Add video", "", "Video (*.mp4 *.mkv *.avi *.mov *.webm)")
        if files:
            self._add_items(files, video=True)
            for full in files:
                idx = self._find_track(full)
                if idx >= 0:
                    self.play_index(idx)
                    break

    def _refresh_video_list(self):
        if not hasattr(self, "video_list"):
            return
        self._video_paths = [t["path"] for t in self.tracks if t["path"].lower().endswith(VIDEO_EXTS)]
        self.video_list.clear()
        for path in self._video_paths:
            self.video_list.addItem(QListWidgetItem(Path(path).stem))
        has_videos = len(self._video_paths) > 0
        self.video_list.setVisible(has_videos)
        if hasattr(self, "video_empty"):
            self.video_empty.setVisible(not has_videos)

    def on_video_clicked(self, item):
        row = self.video_list.row(item)
        if 0 <= row < len(getattr(self, "_video_paths", [])):
            idx = self._find_track(self._video_paths[row])
            if idx >= 0:
                self.play_index(idx)

    def add_subtitles(self):
        path, _ = QFileDialog.getOpenFileName(self, "Add subtitles", "", "Subtitles (*.srt *.ass *.ssa *.vtt *.sub)")
        if path:
            if self.vlc.set_subtitle(path):
                QMessageBox.information(self, "Subtitles", f"Subtitles loaded: {Path(path).name}")
            else:
                QMessageBox.information(self, "Subtitles", "Could not load that subtitle file.")

    def add_video_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose video folder")
        if not folder:
            return
        new = [(full, stem) for full, stem in scan_folder(folder, self._track_paths) if full.lower().endswith(VIDEO_EXTS)]
        if not new:
            QMessageBox.information(self, "No videos", "No video files found in that folder.")
            return
        self._add_items([full for full, _ in new], video=True)
        if folder not in self._video_folders:
            self._video_folders.append(folder); save_video_folders(self._video_folders)
        self._refresh_video_list()
        idx = self._find_track(new[0][0])
        if idx >= 0:
            self.play_index(idx)

    def _is_video_current(self):
        return (self._mode == "local" and 0 <= self.current_index < len(self.tracks)
                and self.tracks[self.current_index]["path"].lower().endswith(VIDEO_EXTS))

    def _play_next_video(self, step=1):
        paths = getattr(self, "_video_paths", [])
        if not paths:
            return False
        cur = self.tracks[self.current_index]["path"] if 0 <= self.current_index < len(self.tracks) else ""
        try:
            i = paths.index(cur)
        except ValueError:
            i = -1
        j = i + step
        if 0 <= j < len(paths):
            idx = self._find_track(paths[j])
            if idx >= 0:
                self.play_index(idx)
                return True
        return False

    def toggle_dock_bar(self):
        if self.dock.isVisible():
            self.dock.hide()
            self.btn_dock_toggle.setText("⌃")
        else:
            self.dock.show()
            self.btn_dock_toggle.setText("⌄")

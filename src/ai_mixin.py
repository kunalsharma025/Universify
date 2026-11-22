class AiMixin:
    def _current_song(self):
        if self._mode == "online" and (t := self._pending_online):
            return t.get("title", ""), t.get("artist", "")
        if 0 <= self.current_index < len(self.tracks):
            info = self.get_info(self.tracks[self.current_index]["path"])
            return info["title"], info["artist"]
        return "", ""

    def ask_ai(self):
        from .ai import answer_question, get_lyrics
        text = self.ai_box.text().strip()
        if not text:
            self.show_ai_info()
            return
        low = text.lower()
        if "play" in low and (q := low.replace("play", "").strip()):
            self.search_box.setText(q)
            self.show_page(2)
            self.search_online()
            self.lbl_ai.setText(f"Playing: {q}")
            return
        title, artist = self._current_song()
        if not title:
            self.lbl_ai.setText("Play a song first, then ask me about it.")
            return
        if "bpm" in low and self._mode != "online":
            self.show_ai_info()
            return
        self.lbl_ai.setText(answer_question(text, title, artist, self._mode == "online"))
        if "lyric" in low:
            self.lbl_big_lyrics.setText(get_lyrics(title, artist)[:300])

    def _load_lyrics(self, title, artist):
        key = f"{title} - {artist}".lower()
        self._lyrics_key, self._lyrics_synced, self._lyrics_idx = key, [], -2
        self.lbl_big_lyrics.setText("")
        if not title:
            return
        self._retire_thread("_lyrics_thread")
        from .online import LyricsWorker
        w = self._lyrics_thread = LyricsWorker(key, title, artist)
        w.done.connect(self._on_lyrics_done)
        w.start()

    def _on_lyrics_done(self, key, plain, synced):
        if key != self._lyrics_key:
            return
        self._lyrics_synced = synced or []
        self.lbl_big_lyrics.setText("\n".join(t for _ms, t in synced[:2]) if synced else plain[:300])

    def _update_lyrics_line(self, pos):
        if not self._lyrics_synced:
            return
        idx = max((i for i, (ms, _t) in enumerate(self._lyrics_synced) if ms <= pos), default=-1)
        if idx == self._lyrics_idx:
            return
        self._lyrics_idx = idx
        if idx < 0:
            self.lbl_big_lyrics.setText("♪")
        else:
            self.lbl_big_lyrics.setText("\n".join(t for _ms, t in self._lyrics_synced[idx:idx + 2]))

    def show_ai_info(self):
        from .ai import get_lyrics, get_summary, get_features, get_hf_mood

        def _show(title, artist, head):
            lyrics = get_lyrics(title, artist)
            self.lbl_ai.setText(f"{head}\n{get_summary(lyrics)}\n\n{lyrics[:500]}")
            self.lbl_big_lyrics.setText(lyrics[:300])

        if self._mode == "online" and self._pending_online:
            t = self._pending_online
            _show(t["title"], t.get("artist", ""), f"Now playing: {t['title']} - {t.get('artist','')}")
            return
        if self.current_index < 0:
            self.lbl_ai.setText("Play a local song first, then come back here.")
            return
        path = self.tracks[self.current_index]["path"]
        self.lbl_ai.setText("Loading AI info... BPM can take a few seconds.")
        try:
            info = self.get_info(path)
            bpm = get_features(path).get("bpm")
            bpm_txt = f"BPM: {bpm or '-'}"
            self.lbl_bpm.setText(bpm_txt)
            _show(info["title"], info["artist"], f"{bpm_txt}\nMood: {get_hf_mood(path) or '-'}")
        except Exception as e:
            self.lbl_ai.setText(f"AI info failed: {e}")


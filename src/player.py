import sys
import vlc


class VlcPlayer:
    def __init__(self):
        self.instance = vlc.Instance("--no-video-title-show")
        self.player = self.instance.media_player_new()
        self.player.audio_set_volume(70)

    def _play(self, media, user_agent=False):
        m = self.instance.media_new(media)
        if user_agent:
            m.add_option(":http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")
        self.player.set_media(m)
        self.player.play()

    def play_path(self, path): self._play(path)
    def play_url(self, url): self._play(url, user_agent=True)
    def set_paused(self, paused): self.player.set_pause(1 if paused else 0)
    def is_playing(self): return bool(self.player.is_playing())

    def is_ended(self):
        try:
            return self.player.get_state() == vlc.State.Ended
        except Exception:
            return False

    def set_volume(self, value): self.player.audio_set_volume(value)
    def get_length(self): return self.player.get_length()
    def get_time(self): return self.player.get_time()
    def set_time(self, ms): self.player.set_time(ms)

    def attach_video(self, win_id):
        setters = {"linux": "set_xwindow", "win32": "set_hwnd", "darwin": "set_nsobject"}
        for prefix, name in setters.items():
            if sys.platform.startswith(prefix):
                getattr(self.player, name)(win_id)
                return

    def set_subtitle(self, path):
        try:
            return self.player.video_set_subtitle_file(path) == 0
        except Exception:
            return False

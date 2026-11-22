from PySide6.QtCore import QThread, Signal
import requests, gettext as _gettext, socket, time, re, html

# ytmusicapi looks for a translation file that PyInstaller does not pack - use no translation instead of crashing
_orig_translation = _gettext.translation


def _safe_translation(*args, **kwargs):
    try:
        return _orig_translation(*args, **kwargs)
    except Exception:
        return _gettext.NullTranslations()


_gettext.translation = _safe_translation

OFFLINE_MSG = "You are offline. Connect to internet please."
from .accounts import _ytmusic
UA = {"User-Agent": "Mozilla/5.0"}


_offline_cache = [0, False]


def is_offline():
    if time.time() - _offline_cache[0] < 10:
        return _offline_cache[1]
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3).close()
        _offline_cache[0], _offline_cache[1] = time.time(), False
        return False
    except Exception:
        _offline_cache[0], _offline_cache[1] = time.time(), True
        return True


# When YouTube fails, rest it for a while and let JioSaavn/Audius carry the app,
# instead of hammering a blocked YouTube again and again.
_yt_rest_until = [0.0]


def _youtube_resting():
    return time.time() < _yt_rest_until[0]


def _youtube_rest(minutes=10):
    _yt_rest_until[0] = time.time() + minutes * 60


def _big_thumb_url(url):
    if "googleusercontent.com" in url:
        return re.sub(r"=w\d+-h\d+", "=w544-h544", url)
    if "i.ytimg.com" in url:
        return url.replace("/mqdefault.jpg", "/hqdefault.jpg").replace("/default.jpg", "/hqdefault.jpg")
    return url


def _thumb(r, last=False):
    try:
        thumbs = r.get("thumbnails", [])
        url = (thumbs[-1] if last else thumbs[0]).get("url", "") if thumbs else ""
        return _big_thumb_url(url) if last else url
    except Exception:
        return ""


def _thumb_data(url):
    if not url:
        return b""
    try:
        r = requests.get(url, timeout=10, headers=UA)
        return r.content if r.status_code == 200 else b""
    except Exception:
        return b""


def _fill_thumbs(out):
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as ex:
            datas = list(ex.map(_thumb_data, [o.get("thumb", "") for o in out]))
    except Exception:
        datas = [b""] * len(out)
    for o, d in zip(out, datas):
        o["thumb_data"] = d
    return out


def _track(**kw):
    return {"videoId": "", "title": "", "artist": "", "thumb": "", "thumb_big": "",
            "thumb_data": b"", "source": "youtube", "duration": 0, **kw}


def _names(items):
    return ", ".join(a.get("name", "") for a in items or [])


def _yt_tracks(results):
    return [_track(videoId=r.get("videoId", ""), title=r.get("title", ""), artist=_names(r.get("artists", [])),
                   thumb=_thumb(r), thumb_big=_thumb(r, last=True)) for r in results]


def _saavn(call, **params):
    r = requests.get("https://www.jiosaavn.com/api.php", params={"__call": call, "api_version": "4", "_format": "json", **params},
                     timeout=10, headers={**UA, "Referer": "https://www.jiosaavn.com/"})
    r.raise_for_status()
    return r.json()


def saavn_search(query, limit=10):
    out = []
    for item in _saavn("search.getResults", q=query, p="1", n=str(limit)).get("results", [])[:limit]:
        info, img = item.get("more_info", {}) or {}, item.get("image", "") or ""
        artist = html.unescape(_names(info.get("artistMap", {}).get("primary_artists", [])))
        out.append(_track(videoId=item.get("id", ""), title=html.unescape(item.get("title", "")), artist=artist, thumb=img,
                          thumb_big=img.replace("150x150", "500x500") if img else "", source="saavn",
                          enc=info.get("encrypted_media_url", ""), is_320=info.get("320kbps") == "true",
                          duration=int(info.get("duration") or item.get("duration") or 0)))
    if not out:
        raise ValueError("JioSaavn found nothing")
    return out


def saavn_stream_url(enc, is_320=True):
    for bitrate in (["320", "160"] if is_320 else ["160", "320"]):
        url = _saavn("song.generateAuthToken", url=enc, bitrate=bitrate).get("auth_url", "")
        if url:
            return url, int(bitrate), 44100
    raise ValueError("JioSaavn stream failed")


def audius_search(query, limit=10):
    r = requests.get("https://discoveryprovider.audius.co/v1/tracks/search", params={"query": query, "app_name": "Universify"}, timeout=10, headers=UA)
    r.raise_for_status()
    out = []
    for item in r.json().get("data", [])[:limit]:
        art = item.get("artwork") or {}
        out.append(_track(videoId=item.get("id", ""), title=item.get("title", ""), artist=(item.get("user") or {}).get("name", ""),
                          thumb=art.get("150x150", ""), thumb_big=art.get("1000x1000") or art.get("480x480") or art.get("150x150", ""),
                          source="audius", duration=int(item.get("duration") or 0)))
    if not out:
        raise ValueError("Audius found nothing")
    return out


def audius_stream_url(track_id):
    return f"https://discoveryprovider.audius.co/v1/tracks/{track_id}/stream?app_name=Universify"


def _fallback(query, limit=10):
    for fn in (saavn_search, audius_search):
        try:
            if out := fn(query, limit=limit):
                return out
        except Exception:
            pass
    return None


class LyricsWorker(QThread):
    done = Signal(str, str, list)

    def __init__(self, key, title, artist):
        super().__init__()
        self.key, self.title, self.artist = key, title, artist

    def run(self):
        from .ai import get_lyrics_full
        try:
            plain, synced = get_lyrics_full(self.title, self.artist)
        except Exception:
            plain, synced = "", []
        self.done.emit(self.key, plain, synced)


class SearchWorker(QThread):
    done = Signal(list)
    failed = Signal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        if is_offline():
            self.failed.emit(OFFLINE_MSG)
            return
        out = []
        if not _youtube_resting():
            results = None
            for wait in (0, 1, 2, 4):
                time.sleep(wait)
                try:
                    results = _ytmusic().search(self.query, filter="songs", limit=10)
                    break
                except Exception:
                    pass
            out = _yt_tracks(results or [])
            if results is None:
                _youtube_rest(10)
        if out:
            self.done.emit(out)
            return
        out = _fallback(self.query)
        if out:
            self.done.emit(out)
        else:
            self.failed.emit("YouTube and backups all failed. Try again in a bit, or play a local song.")


class ThumbWorker(QThread):
    done = Signal(list)

    def __init__(self, results):
        super().__init__()
        self.results = results

    def run(self):
        self.done.emit(_fill_thumbs(self.results))


class StreamWorker(QThread):
    done = Signal(str, int, int, int)
    failed = Signal(str, int)

    def __init__(self, video_id, track=None, token=0, backup_only=False):
        super().__init__()
        self.video_id, self.track = video_id, track or {}
        self.token = token
        self.backup_only = backup_only

    def run(self):
        if is_offline():
            self.failed.emit(OFFLINE_MSG, self.token)
            return
        try:
            if self.track.get("source") == "audius" and self.track.get("videoId"):
                self.done.emit(audius_stream_url(self.track["videoId"]), 128, 44100, self.token)
                return
            if self.track.get("source") == "saavn" and self.track.get("enc"):
                self.done.emit(*saavn_stream_url(self.track["enc"], self.track.get("is_320", True)), self.token)
                return
            if not self.backup_only:
                import yt_dlp
                info = None
                for cookies in (("chrome",), None):
                    opts = {"format": "bestaudio", "quiet": True, "noplaylist": True, "socket_timeout": 5, "retries": 1,
                            "remote_components": ["ejs:github"],
                            "extractor_args": {"youtube": {"player_client": ["tv", "ios", "web"]}},
                            **({"cookiesfrombrowser": cookies} if cookies else {})}
                    try:
                        with yt_dlp.YoutubeDL(opts) as ydl:
                            info = ydl.extract_info(f"https://music.youtube.com/watch?v={self.video_id}", download=False)
                        break
                    except Exception:
                        continue
                if info:
                    abr, asr = info.get("abr") or 0, info.get("asr") or 0
                    if not abr:
                        abr, asr = next(((f["abr"], f.get("asr") or asr) for f in info.get("formats") or [] if f.get("abr")), (abr, asr))
                    self.done.emit(info.get("url", ""), int(abr or 0), int(asr or 0), self.token)
                    return
        except Exception:
            pass
        title = ((self.track.get("title") or "") + " " + (self.track.get("artist") or "")).strip()
        cands = []
        for fn in (saavn_search, audius_search):
            try:
                cands += fn(title, limit=5)
            except Exception:
                pass
        for o in cands:
            try:
                if o.get("source") == "saavn" and o.get("enc"):
                    self.done.emit(*saavn_stream_url(o["enc"], o.get("is_320", True)), self.token)
                    return
                if o.get("source") == "audius" and o.get("videoId"):
                    self.done.emit(audius_stream_url(o["videoId"]), 128, 44100, self.token)
                    return
            except Exception:
                continue
        self.failed.emit("no stream found", self.token)


class ChartWorker(QThread):
    done = Signal(list, str)
    failed = Signal(str)

    def __init__(self, kind):
        super().__init__()
        self.kind = kind

    def run(self):
        if is_offline():
            self.failed.emit(OFFLINE_MSG)
            return
        q = {"india": "Top Hits India 2026", "world": "Top Hits Global 2026", "indie": "Indie India", "trending": "Trending India"}.get(self.kind, "Top Hits India")
        if not _youtube_resting():
            try:
                yt = _ytmusic()
                out = []
                if self.kind in ("india", "world"):
                    try:
                        charts = yt.get_charts(country="IN" if self.kind == "india" else "ZZ")
                        items = charts.get("countries", {}).get("items", []) if isinstance(charts, dict) else []
                        out = _yt_tracks(items[:10])
                    except Exception:
                        pass
                if not out:
                    out = _yt_tracks(yt.search(q, filter="songs", limit=10))
                if out:
                    self.done.emit(out, self.kind)
                    return
            except Exception:
                pass
            _youtube_rest(10)
        out = _fallback(q)
        if out:
            self.done.emit(out, self.kind)
        else:
            self.failed.emit("Charts failed on all sources.")

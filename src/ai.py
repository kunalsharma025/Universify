import os
import re
import requests


def _clean_title(title):
    return re.split(r"\s*[\(\[]", title or "")[0].split(" - ")[0].strip()


def _same(a, b):
    a, b = [re.sub(r"[^a-z0-9]", "", (s or "").lower()) for s in (a, b)]
    return bool(a and b) and (a == b or a in b or b in a)


def parse_synced(text):
    return [((int(m.group(1)) * 60 + int(m.group(2))) * 1000 + int(m.group(3)) * 10, m.group(4).strip())
            for line in (text or "").splitlines()
            if (m := re.match(r"\[(\d+):(\d+)[.:](\d+)\]\s*(.*)", line)) and m.group(4).strip()]


def get_lyrics_full(title, artist):
    for name in (_clean_title(title), (title or "").strip()):
        d = _get_json("https://lrclib.net/api/get", params={"artist_name": artist, "track_name": name}) if name else None
        if not d:
            continue
        if _same(d.get("trackName", ""), name) and _same(d.get("artistName", ""), artist):
            return (d.get("plainLyrics", "") or "", parse_synced(d.get("syncedLyrics", "") or ""))
        return "", []
    return "", []


def _get_json(url, **kw):
    try:
        r = requests.get(url, timeout=10, **kw)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def get_lyrics(title, artist):
    return get_lyrics_full(title, artist)[0]


def get_summary(lyrics):
    if not lyrics:
        return ""
    w = lyrics.lower()
    mood = "happy" if any(x in w for x in ("love", "happy", "dance", "smile")) else "sad" if any(x in w for x in ("cry", "pain", "miss", "alone")) else "calm"
    lines = [l.strip() for l in lyrics.splitlines() if l.strip()]
    return f"{mood} song. {len(lines)} lines. About: {lines[0][:80]}" if lines else ""


def get_features(path):
    try:
        import librosa
        y, sr = librosa.load(path, sr=22050, mono=True, duration=30)
        return {"bpm": round(float(librosa.beat.beat_track(y=y, sr=sr)[0]), 1)}
    except Exception:
        return {"bpm": None}


def answer_question(text, title, artist, is_online):
    low = text.lower()
    lyrics = get_lyrics(title, artist) if any(k in low for k in ("lyric", "mood", "summary", "about")) else ""
    if "lyric" in low:
        return f"{title} - {artist}\n\n{lyrics[:800]}" if lyrics else f"No lyrics found for {title}."
    if "singer" in low or "artist" in low or "who" in low:
        return f"Singer: {artist or '-'}"
    if "bpm" in low:
        return "BPM needs a local file, I can't measure it from an online stream." if is_online else "BPM"
    if "mood" in low or "summary" in low or "about" in low:
        return f"{title} - {artist}\n{get_summary(lyrics) or 'No summary, no lyrics found.'}"
    if "name" in low or "what" in low or "song" in low:
        return f"Song name is {title} - {artist}"
    return f"You are listening to {title} - {artist}.\nAsk me: what is the name, who is the singer, show lyrics, or play a song."


def get_hf_mood(path):
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        return ""
    try:
        with open(path, "rb") as f: data = f.read()
        r = requests.post("https://router.huggingface.co/hf-inference/models/laion/clap-htsat-unfused",
                          headers={"Authorization": f"Bearer {token}"}, data=data, timeout=30)
        out = r.json() if r.status_code == 200 else []
        return out[0].get("label", "") if isinstance(out, list) and out else ""
    except Exception:
        return ""

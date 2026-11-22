import json
import sys
from pathlib import Path

FILE = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent.parent) / "library.json"
LAST_FILE = FILE.parent / "last_played.json"
FAV_FILE = FILE.parent / "favourites.json"

def _load(path):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None

def _dump(path, data, indent=None):
    try: path.write_text(json.dumps(data, indent=indent), encoding="utf-8")
    except Exception: pass

def _read_all():
    data = _load(FILE)
    return data if isinstance(data, dict) else {}

def load_folders():
    data = _read_all()
    if not isinstance(data, (dict, list)):
        return []
    folders = data.get("folders", []) if isinstance(data, dict) else data
    return [f for f in folders if isinstance(f, str) and Path(f).is_dir()]

def save_folders(folders):
    data = _read_all()
    data["folders"] = list(dict.fromkeys(folders))
    _dump(FILE, data, indent=2)

def load_video_folders():
    data = _read_all()
    folders = data.get("video_folders", [])
    return [f for f in folders if isinstance(f, str) and Path(f).is_dir()]

def save_video_folders(folders):
    data = _read_all()
    data["video_folders"] = list(dict.fromkeys(folders))
    _dump(FILE, data, indent=2)

def load_last():
    try:
        data = _load(LAST_FILE)
        if not isinstance(data, dict):
            return None
        if data.get("kind") == "online" and data.get("track", {}).get("videoId"):
            return {"kind": "online", "pos": int(data.get("pos", 0)), "track": data["track"]}
        path = data.get("path", "")
        if isinstance(path, str) and Path(path).is_file():
            return {"kind": "local", "path": path, "pos": int(data.get("pos", 0))}
    except Exception:
        pass
    return None

def load_favourites():
    data = _load(FAV_FILE)
    return [d for d in data if isinstance(d, dict) and d.get("title")] if isinstance(data, list) else []

def save_favourites(favs):
    _dump(FAV_FILE, favs, indent=2)

def _save(data):
    _dump(LAST_FILE, data)

def save_last(path, pos):
    _save({"kind": "local", "path": path, "pos": int(max(0, pos))})

def save_online(track, pos):
    keep = {k: track.get(k, "") for k in ("videoId", "title", "artist", "source", "thumb", "thumb_big", "enc")}
    keep["is_320"] = bool(track.get("is_320", True))
    _save({"kind": "online", "pos": int(max(0, pos)), "track": keep})

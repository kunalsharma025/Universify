from pathlib import Path
from mutagen import File as MutagenFile

def _tag(audio, *keys):
    if audio is None or getattr(audio, "tags", None) is None:
        return ""
    for key in keys + tuple(k.lower() for k in keys):
        try: value = audio.tags.get(key)
        except Exception: continue
        if value:
            return str(value[0] if isinstance(value, list) else value).strip()
    return ""

FORMATS = {"FLAC": "FLAC", "MP3": "MP3", "WAVE": "WAV", "MP4": "MP4 / M4A", "OGG": "OGG"}

def _true_format(audio):
    cls = type(audio).__name__.upper()
    mime = " ".join(getattr(audio, "mime", []) or []).lower()
    for k, v in FORMATS.items():
        if k in cls or k.lower() in mime:
            return v
    return cls

def inspect_audio(path):
    path = str(path)
    ext = Path(path).suffix.lower()
    result = {"path": path, "true_format": "Unknown", "bit_depth": None, "sample_rate": None,
              "bitrate": None, "channels": None, "duration": None, "title": Path(path).stem,
              "artist": "", "album": "", "is_fake_flac": False, "warning": ""}
    try:
        magic = open(path, "rb").read(4)
    except OSError as e:
        result["warning"] = f"Cannot read file: {e}"
        return result
    try: audio = MutagenFile(path)
    except Exception: audio = None
    if audio is None:
        from mutagen.flac import FLAC
        from mutagen.mp3 import MP3
        from mutagen.oggvorbis import OggVorbis
        from mutagen.wave import WAVE
        for parser in (FLAC, WAVE, MP3, OggVorbis):
            try:
                audio = parser(path)
                break
            except Exception:
                pass
    if audio is None:
        result["is_fake_flac"] = ext == ".flac" and magic != b"fLaC"
        result["warning"] = ("FAKE FLAC - header is not fLaC, file was renamed." if result["is_fake_flac"]
                             else "Mutagen could not read this file.")
        return result
    info = audio.info
    result.update(duration=getattr(info, "length", None), channels=getattr(info, "channels", None),
                  sample_rate=getattr(info, "sample_rate", None),
                  bitrate=int(getattr(info, "bitrate", 0) // 1000) or None,
                  bit_depth=getattr(info, "bits_per_sample", None), true_format=_true_format(audio))
    if ext == ".flac" and (result["true_format"] != "FLAC" or magic != b"fLaC"):
        result["is_fake_flac"] = True
        result["warning"] = (f"FAKE FLAC - file is actually {result['true_format']}, not FLAC. Extension was renamed."
                             if result["true_format"] != "FLAC" else "FAKE FLAC - header is not fLaC, lossy file renamed.")
    elif result["true_format"] in ("MP3", "OGG", "MP4 / M4A") and result["bit_depth"] is None:
        result["warning"] = "Lossy format - no true bit depth."
    for field, keys in (("title", ("TIT2", "title", "\xa9nam")), ("artist", ("TPE1", "artist", "\xa9ART")),
                        ("album", ("TALB", "album", "\xa9alb"))):
        v = _tag(audio, *keys)
        if v:
            result[field] = v
    return result

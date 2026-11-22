from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QGridLayout, QLabel
from .config import PANEL, TEXT, RED
from .visualizer import CircleWaveCover


def _fmt_sec(s):
    return f"{int(s // 60)}:{int(s % 60):02d}" if s else "-"


def build_inspector(p):
    inspector = QFrame()
    p.inspector = inspector
    inspector.setFixedWidth(280)
    inspector.setStyleSheet(f"background:{PANEL}; border-left:1px solid rgba(255,255,255,0.08); border-radius: 18px;")
    ins = QVBoxLayout(inspector)
    ins.setContentsMargins(16, 16, 16, 12)
    ins.setAlignment(Qt.AlignTop)
    p.lbl_cover = CircleWaveCover()
    p.lbl_cover.setToolTip("Click for fullscreen Now Playing")
    p.lbl_cover.setCursor(Qt.PointingHandCursor)
    p.lbl_cover.mousePressEvent = lambda _e: p.open_fullscreen_now()
    ins.addWidget(p.lbl_cover, 0, Qt.AlignCenter)
    p._set_cover(None, None)
    head2 = QLabel("Audio Telemetry")
    head2.setStyleSheet("font-size:16px; font-weight:bold;")
    ins.addWidget(head2)
    grid = QGridLayout()
    for i, (attr, name) in enumerate((("lbl_format", "CODEC"), ("lbl_bits", "DEPTH"),
                                      ("lbl_rate", "RATE"), ("lbl_bitrate", "BITRATE"))):
        lbl = QLabel(f"{name}\n-")
        lbl.setStyleSheet("background:#0A0B10; padding:10px; border-radius:12px; color:" + TEXT + ";")
        setattr(p, attr, lbl)
        grid.addWidget(lbl, i // 2, i % 2)
    ins.addLayout(grid)
    p.lbl_warn = QLabel("")
    p.lbl_warn.setStyleSheet(f"color:{RED}; font-weight:bold;")
    p.lbl_warn.setWordWrap(True)
    ins.addWidget(p.lbl_warn)
    for attr, text in (("lbl_channels", "Channels: -"), ("lbl_duration", "Duration: -"),
                       ("lbl_title", "Title: -"), ("lbl_artist", "Artist: -")):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        setattr(p, attr, lbl)
        ins.addWidget(lbl)
    ins.addStretch()
    return inspector


def _set(p, fmt, bits, rate, br, title, artist, dur="-", channels="-", warn=""):
    for attr, text in (("lbl_format", f"CODEC\n{fmt}"), ("lbl_bits", f"DEPTH\n{bits}"),
                       ("lbl_rate", f"RATE\n{rate}"), ("lbl_bitrate", f"BITRATE\n{br}"),
                       ("lbl_title", f"Title: {title}"), ("lbl_artist", f"Artist: {artist or '-'}"),
                       ("lbl_duration", f"Duration: {dur}"), ("lbl_channels", f"Channels: {channels}"),
                       ("lbl_warn", warn)):
        getattr(p, attr).setText(text)


def set_local_telemetry(p, info):
    bits = f"{info['bit_depth']}-bit" if info["bit_depth"] else "Lossy"
    rate = f"{info['sample_rate'] / 1000:.1f} kHz" if info["sample_rate"] else "-"
    br = f"{info['bitrate']} kbps" if info["bitrate"] else "-"
    _set(p, info["true_format"], bits, rate, br, info["title"], info["artist"],
         _fmt_sec(info["duration"]), info["channels"] or "-", info["warning"])
    p.lbl_now_title.setText(f"{info['title']} - {info['artist']}" if info["artist"] else info["title"])
    p.lbl_quality.setText(f"{info['true_format']}  {bits}  {rate}" if info["bit_depth"] else f"{info['true_format']}  {br}")


def set_online_telemetry(p, track, abr=0, asr=0):
    p.lbl_quality.setText("YT STREAM")
    _set(p, "Online stream", "-", f"{asr / 1000:.1f} kHz" if asr else "-",
         f"{int(abr)} kbps" if abr else "stream only", track["title"], track["artist"], "stream")


def set_online_duration(p, length_ms):
    p.lbl_duration.setText(f"Duration: {_fmt_sec(length_ms / 1000) if length_ms else '-'}")
